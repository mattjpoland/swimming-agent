from flask import g, Response
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from src.agent.gateways.openAIGateway import OpenAIGateway
from src.agent.registry import registry
from src.domain.services.ragQueryingService import query_rag
from src.agent.services.promptService import PromptService

# Import new response objects
from src.agent.responses.base import ActionResponse
from src.agent.responses.text import TextResponse, ErrorResponse, DirectResponse
from src.agent.responses.special import ImageResponse, FileResponse
from src.agent.responses.tool import ToolSelectionResponse, ToolExecutionResponse

@dataclass
class InformationResponse:
    answer: str
    source_count: int
    confidence: float

class AgentService:
    def __init__(self):
        self.openai_gateway = OpenAIGateway()
        self.prompt_service = PromptService()

    def process_chat(self, user_input: str, context: Dict[str, Any] = None, 
                    response_format: str = "auto",
                    conversation_history: List[Dict] = None) -> Tuple[Union[Dict, Response], int, List[Dict]]:
        """
        Process a chat request through the complete agent pipeline in two main stages:
        
        STAGE 1 - TOOL SELECTION:
        REQUEST > SERVER > AGENT_SERVICE > AI_CALL_1 > TOOL_SELECTION > REGISTRY > ACTION_EXECUTION
        
        STAGE 2 - RESPONSE GENERATION:
        ACTION_RESULT > AI_CALL_2 > FINAL_RESPONSE > HTTP RESPONSE
        
        Returns:
            Tuple containing:
            - The response data (Dict or Response object)
            - Status code (int)
            - Updated conversation history (List[Dict])
        """
        try:
            # Normalize parameters
            context = context or {}
            conversation_history = conversation_history or []
            
            # Store context in flask g for action execution if it's not already there
            if context and not hasattr(g, 'context'):
                g.context = context
            
            # STAGE 1: Tool selection and execution
            stage1_response = self._perform_tool_selection_stage(user_input, conversation_history, response_format)
            
            # Keep track of the updated conversation history
            updated_history = conversation_history.copy()
            
            # Add user message to history
            updated_history.append({
                "role": "user", 
                "content": user_input
            })
            
            # If it's a direct response (not requiring the second AI call) or an error, return it immediately
            if not stage1_response.requires_second_ai_call or stage1_response.response_type == "error":
                response_data, status_code = stage1_response.to_http_response()
                
                # Add assistant's response to history
                if hasattr(stage1_response, 'content'):
                    updated_history.append({
                        "role": "assistant",
                        "content": stage1_response.content
                    })
                
                return response_data, status_code, updated_history
                
            # STAGE 2: Response generation based on tool result
            final_response = self._perform_response_generation_stage(stage1_response)
            
            # Get the response data and status code
            response_data, status_code = final_response.to_http_response()
            
            # Add assistant's response to history
            if hasattr(final_response, 'content'):
                updated_history.append({
                    "role": "assistant",
                    "content": final_response.content
                })
                
            # If there was a tool interaction, add it to history
            if hasattr(stage1_response, 'tool_call') and hasattr(stage1_response, 'action'):
                # Get tool name and args
                tool_name = stage1_response.tool_call.function.name
                tool_args = stage1_response.tool_call.function.arguments
                
                # Add tool calls to history in OpenAI format
                updated_history.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": stage1_response.tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_args
                        }
                    }]
                })
                
                # Add tool response
                if hasattr(stage1_response, 'result'):
                    updated_history.append({
                        "role": "tool",
                        "tool_call_id": stage1_response.tool_call.id,
                        "content": str(self._get_result_as_string(stage1_response.result))
                    })
            
            return response_data, status_code, updated_history
            
        except Exception as e:
            logging.error(f"Error in agent service: {e}", exc_info=True)
            error_response = ErrorResponse("Failed to process request", str(e))
            response_data, status_code = error_response.to_http_response()
            return response_data, status_code, conversation_history

    def _perform_tool_selection_stage(self, user_input: str, conversation_history: List[Dict], 
                                     response_format: str = "auto") -> ActionResponse:
        """
        Performs Stage 1 - Tool selection and execution
        
        Returns an ActionResponse subclass instance appropriate to the result
        """
        # Prepare prompt for tool selection
        messages = self._prepare_tool_selection_prompt(user_input, conversation_history)
        
        # Get available tools
        tools = self._get_available_tools()
        
        # Make AI call for tool selection
        try:
            response = self._make_tool_selection_call(messages, tools)
        except Exception as e:
            logging.error(f"Stage 1 failed: Error in tool selection AI call: {e}")
            return ErrorResponse(
                "I'm sorry, I encountered a problem while processing your request.", 
                str(e)
            )
            
        # Process AI response (execute tool or return direct text)
        message = response.choices[0].message
        tool_calls = message.tool_calls

        # If no tool calls, this is a direct text response
        if not tool_calls:
            logging.info("No tool calls detected, returning direct text response")
            return DirectResponse(message.content)

        # Handle tool call
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        logging.info(f"Tool call detected: {function_name} with arguments: {tool_call.function.arguments}")
        
        # Get the action from registry
        action = registry.get_action(function_name)
        if not action:
            return ErrorResponse(
                f"I don't know how to {function_name} yet.",
                status_code=400
            )
        
        # Create tool selection response
        tool_selection = ToolSelectionResponse(tool_call, messages, user_input)
        
        # Execute the action
        try:
            action_result = self._execute_action(action, tool_call, user_input, response_format)
        except Exception as e:
            logging.error(f"Error executing action {function_name}: {e}", exc_info=True)
            return ErrorResponse(
                f"I encountered an error while trying to {function_name}.",
                str(e)
            )
        
        # Check for special response types
        if isinstance(action_result, Response) and action_result.mimetype == "image/png":
            # Pass the Response object directly to ImageResponse without extracting data
            return ImageResponse(action_result)
        
        # Check for tuple with Response
        if isinstance(action_result, tuple) and len(action_result) == 2:
            response_obj, status_code = action_result
            # Handle tuple with image response
            if isinstance(response_obj, Response) and response_obj.mimetype == "image/png":
                return ImageResponse(response_obj, status_code=status_code)
                
        # For all other cases, return tool execution response
        return ToolExecutionResponse(tool_call, action, action_result, messages)
    
    def _prepare_tool_selection_prompt(self, user_input: str, conversation_history: List[Dict]) -> List[Dict]:
        """Prepares the prompt for tool selection"""
        return self.prompt_service.generate_initial_tool_selection_prompt(user_input, conversation_history)
    
    def _get_available_tools(self) -> List[Dict]:
        """Gets available tools from the registry"""
        return registry.get_tools_for_openai()
    
    def _make_tool_selection_call(self, messages: List[Dict], tools: List[Dict]) -> Any:
        """Makes the AI call for tool selection"""
        response = self.openai_gateway.get_completion(messages, tools)
        logging.info("Stage 1 completed: Tool selection AI call successful")
        return response
    
    def _execute_action(self, action: Any, tool_call: Any, user_input: str, 
                       response_format: str = "auto") -> Any:
        """Executes the selected action with the provided parameters"""
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            logging.error("Failed to parse tool arguments as JSON")
            raise ValueError("Failed to parse tool arguments as JSON")

        # Get context from Flask g if available
        context = getattr(g, 'context', {})

        # Execute the action
        logging.info(f"Executing action: {tool_call.function.name}")
        return action.execute(
            arguments=arguments,
            context=context,
            user_input=user_input,
            response_format=response_format
        )
    
    def _perform_response_generation_stage(self, tool_execution_response: ToolExecutionResponse) -> ActionResponse:
        """
        Performs Stage 2 - Final response generation
        
        Args:
            tool_execution_response: The result of the tool execution from stage 1
            
        Returns:
            ActionResponse: Final response to send to the user
        """
        # Extract tool result as string
        tool_result = self._get_result_as_string(tool_execution_response.result)
        
        # Update conversation with tool interaction
        updated_messages = self._add_tool_interaction_to_messages(
            tool_execution_response.messages, 
            tool_execution_response.tool_call, 
            tool_result
        )
        
        # Prepare final response prompt
        final_response_messages = self._prepare_final_response_prompt(
            updated_messages, 
            tool_execution_response.action
        )
        
        # Make final AI call
        try:
            logging.info("Making second AI call for final response generation")
            final_ai_response = self.openai_gateway.get_completion(final_response_messages)
            logging.info("Stage 2 completed: Final response AI call successful")
            
            # Parse the content for conversation end marker if present
            content = final_ai_response.choices[0].message.content
            is_conversation_over = False
            
            # Log the raw response content
            logging.debug(f"Stage 2 AI raw response: {content}")
            
            # Check for JSON with is_conversation_over flag
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    response_json = json.loads(content)
                    logging.debug(f"Successfully parsed JSON from stage 2 response: {response_json}")
                    
                    if 'is_conversation_over' in response_json:
                        is_conversation_over = bool(response_json.get('is_conversation_over'))
                        logging.info(f"Stage 2: Set conversation_over flag to: {is_conversation_over}")
                    else:
                        logging.warning("Stage 2: JSON missing 'is_conversation_over' field")
                        
                    if 'message' in response_json:
                        content = response_json.get('message')
                        logging.debug(f"Stage 2: Extracted message from JSON: {content}")
                    else:
                        logging.warning("Stage 2: JSON missing 'message' field")
                except json.JSONDecodeError as e:
                    logging.warning(f"Stage 2: Failed to parse response as JSON: {e}")
                    logging.warning(f"Stage 2: Problem content: {content}")
            else:
                logging.debug("Stage 2: Response is not in JSON format")
            
            # Create text response
            response = TextResponse(content)
            if is_conversation_over:
                response.mark_conversation_over()
                logging.info(f"Stage 2: Marked conversation as over. Final flag value: {response.is_conversation_over}")
            else:
                logging.info(f"Stage 2: Conversation continuing. Flag value: {response.is_conversation_over}")
                
            return response
            
        except Exception as e:
            logging.error(f"Stage 2 failed: Error in final response AI call: {e}")
            return ErrorResponse("Error processing the response", str(e))
        
    def _add_tool_interaction_to_messages(self, messages: List[Dict], tool_call: Any, tool_result: str) -> List[Dict]:
        """Adds the tool interaction to the conversation history"""
        messages_copy = messages.copy()
        messages_copy.extend([
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
        return messages_copy
    
    def _prepare_final_response_prompt(self, messages: List[Dict], action: Any) -> List[Dict]:
        """Prepares the prompt for the final response generation"""
        return self.prompt_service.generate_final_response_prompt(messages, action)
    
    def _get_result_as_string(self, result: Any) -> str:
        """
        Convert any result type to a string representation.
        This replaces the old _extract_tool_result method.
        """
        if isinstance(result, Response):
            try:
                response_data = result.get_data(as_text=True)
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
        
        if isinstance(result, tuple) and len(result) == 2:
            response_obj = result[0]
            if isinstance(response_obj, dict):
                return response_obj.get("message", json.dumps(response_obj))
            if isinstance(response_obj, Response):
                return self._get_result_as_string(response_obj)
            return str(response_obj)
        
        return str(result)

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
            
            # Use base prompt from PromptService with RAG-specific instructions
            base_prompt = self.prompt_service.get_base_system_prompt().split("\n\n")[0]  # Get just the first paragraph
            
            # Prepare prompt for LLM
            messages = [
                {"role": "system", "content": (
                    f"{base_prompt}\n\n"
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