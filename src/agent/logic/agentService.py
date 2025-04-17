from flask import g, Response
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from src.agent.gateways.openAIGateway import OpenAIGateway
from src.agent.registry import registry
from src.utils.rag_querying import query_rag

@dataclass
class InformationResponse:
    answer: str
    source_count: int
    confidence: float

class AgentService:
    def __init__(self):
        self.openai_gateway = OpenAIGateway()

    def process_agent_request(
        self,
        user_input: str,
        response_format: str = "auto",
        is_siri: bool = False,
        conversation_history: List[Dict] = None
    ) -> Tuple[Dict, int]:
        # Build messages array with history
        messages = self._build_messages(user_input, is_siri, conversation_history or [])
        
        # Get tools from registry
        tools = registry.get_tools_for_openai()

        # Get initial completion
        try:
            response = self.openai_gateway.get_completion(messages, tools)
        except Exception as e:
            return {
                "message": "I'm sorry, I encountered a problem while processing your request.", 
                "status": "error",
                "error": str(e),
                "content_type": "application/json"
            }, 500

        # Process the response
        return self._process_completion_response(
            response=response,
            messages=messages,
            user_input=user_input,
            response_format=response_format,
            is_siri=is_siri
        )

    def _build_messages(
        self,
        user_input: str,
        is_siri: bool,
        conversation_history: List[Dict]
    ) -> List[Dict]:
        system_prompt = registry.get_system_prompt()
        if is_siri:
            system_prompt += " Since your response will be read aloud by Siri, keep answers brief, clear, and suitable for voice."
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for message in conversation_history:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
        return messages

    def _process_completion_response(
        self,
        response: Any,
        messages: List[Dict],
        user_input: str,
        response_format: str,
        is_siri: bool
    ) -> Tuple[Union[Dict, Response], int]:
        message = response.choices[0].message
        tool_calls = message.tool_calls

        if not tool_calls:
            # Handle direct text response
            return self._process_text_response(message.content)

        # Process tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        logging.info(f"Function call: {function_name} with arguments: {tool_call.function.arguments}")
        
        action = registry.get_action(function_name)
        if not action:
            return {
                "message": f"I don't know how to {function_name} yet.",
                "status": "error",
                "content_type": "application/json"
            }, 400

        # Execute action and process result
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return {
                "message": "I couldn't understand how to process your request.",
                "status": "error",
                "content_type": "application/json"
            }, 500

        # Get context from Flask g if available, otherwise use empty dict
        context = getattr(g, 'context', {})

        action_response = action.execute(
            arguments=arguments,
            context=context,
            user_input=user_input,
            response_format=response_format,
            is_siri=is_siri
        )

        # Handle Siri-specific availability response
        if is_siri and function_name == "check_lane_availability":
            if isinstance(action_response, tuple) and len(action_response) == 2:
                resp, status = action_response
                if isinstance(resp, Response) and resp.is_streamed:
                    return {
                        "message": "I've checked the lane availability. There are various times available. For a detailed schedule, please check on your device.",
                        "status": "success",
                        "content_type": "application/json"
                    }, 200

        # Handle special responses (images, etc.)
        if isinstance(action_response, Response) and action_response.mimetype == "image/png":
            return action_response, 200

        # Handle tuple responses with Response objects
        if isinstance(action_response, tuple) and len(action_response) == 2:
            response, status_code = action_response
            if isinstance(response, Response) and response.mimetype == "image/png":
                return response, status_code

        # Process tool result through LLM for final response
        return self._process_tool_result(tool_call, action_response, messages)

    def _process_tool_result(
        self,
        tool_call: Any,
        action_response: Any,
        messages: List[Dict]
    ) -> Tuple[Dict, int]:
        tool_result = self._extract_tool_result(action_response)

        # Add tool interaction to messages
        messages.extend([
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                }]
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            }
        ])

        # Get final response
        if tool_call.function.name == "check_appointments":
            messages.append({
                "role": "system",
                "content": "The following is the accurate appointment data. Format your response following these rules:\n" +
                           "1. Your response MUST only include these appointments, DO NOT generate or invent any other appointments\n" +
                           "2. Format appointments in a concise bullet point list\n" +
                           "3. Use the day of week (e.g., 'Monday' or 'Tuesday') instead of the full date (no month/date needed)\n" +
                           "4. Include the time, lane information, and duration\n" + 
                           "5. Do not say 'at Michigan Athletic Club' or 'in the Michigan Athletic Club'\n" +
                           "6. Make the response brief and suitable for quick text-to-speech reading"
            })

        try:
            final_response = self.openai_gateway.get_completion(messages)
            return self._process_text_response(final_response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Error in final response processing: {e}")
            return {
                "message": "Error processing the response",
                "status": "error",
                "content_type": "application/json"
            }, 500

    def _extract_tool_result(self, action_response: Any) -> str:
        """Extract the result string from various response types"""
        if isinstance(action_response, Response):
            try:
                response_data = action_response.get_data(as_text=True)
                if response_data.strip().startswith('{'):
                    try:
                        json_data = json.loads(response_data)
                        return json_data.get("message", response_data)
                    except json.JSONDecodeError:
                        return response_data
                return response_data
            except Exception as e:
                logging.error(f"Error extracting data from Response: {e}")
                return "Error retrieving data from response"
        
        if isinstance(action_response, tuple) and len(action_response) == 2:
            response_obj = action_response[0]
            if isinstance(response_obj, dict):
                return response_obj.get("message", json.dumps(response_obj))
            if isinstance(response_obj, Response):
                return self._extract_tool_result(response_obj)
            return str(response_obj)
        
        return str(action_response)

    def _process_text_response(self, content: str) -> Tuple[Dict, int]:
        """Process a text response into our standard format"""
        is_conversation_over = False
        response_message = content

        # Check for JSON with is_conversation_over flag
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                response_json = json.loads(content)
                is_conversation_over = response_json.get('is_conversation_over', False)
                response_message = response_json.get('message', content)
            except:
                pass

        return {
            "message": response_message,
            "status": "success",
            "content_type": "application/json",
            "is_conversation_over": is_conversation_over
        }, 200

    def get_information_response(self, question: str, context: dict) -> InformationResponse:
        """
        High-level method to handle information requests using RAG and LLM
        """
        try:
            # Query the RAG system
            results = query_rag(question)
            
            if not results:
                return InformationResponse(
                    answer="I'm sorry, I couldn't find specific information about that. Please contact the facility directly.",
                    source_count=0,
                    confidence=0.0
                )
            
            # Combine relevant chunks
            context_text = "\n".join([chunk["text"] for chunk in results])
            
            # Prepare prompt for LLM
            messages = [
                {"role": "system", "content": (
                    "You are a helpful assistant for a swimming facility. "
                    "Use the provided context to answer questions accurately and concisely. "
                    "If the context doesn't fully answer the question, be honest about what you don't know."
                )},
                {"role": "user", "content": f"Using this context:\n\n{context_text}\n\nAnswer this question: {question}"}
            ]
            
            # Get LLM response
            response = self.openai_gateway.get_completion(messages)
            
            # Calculate average confidence from RAG results
            avg_confidence = sum(r.get('similarity', 0) for r in results) / len(results)
            
            return InformationResponse(
                answer=response.choices[0].message.content,
                source_count=len(results),
                confidence=avg_confidence
            )
            
        except Exception as e:
            logging.error(f"Error in AgentService.get_information_response: {e}")
            raise