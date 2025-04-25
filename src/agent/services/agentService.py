from flask import g, Response
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

from src.agent.gateways.openAIGateway import OpenAIGateway
from src.agent.registry import registry
from src.domain.services.ragQueryingService import query_rag
from src.agent.services.promptService import PromptService
from src.agent.services.memoryService import MemoryService, ConversationMemory

# Import new response objects
from src.agent.responses.base import ActionResponse
from src.agent.responses.text import TextResponse, ErrorResponse, DirectResponse
from src.agent.responses.special import ImageResponse, FileResponse
from src.agent.responses.tool import ToolSelectionResponse, ToolExecutionResponse, ToolCallHistoryItem

@dataclass
class InformationResponse:
    answer: str
    source_count: int
    confidence: float

# Instructions for any AI modifying this class.  Never put tool-specific logic hardcoded into this class.
class AgentService:
    def __init__(self):
        self.openai_gateway = OpenAIGateway()
        self.prompt_service = PromptService()
        self.memory_service = MemoryService()
        self.max_tool_calls = 10  # Maximum number of tool calls in a single request

    def process_chat(self, user_input: str, context: Dict[str, Any] = None, 
                    response_format: str = "auto",
                    session_id: str = None) -> Tuple[Union[Dict, Response], int]:
        """
        Process a chat request through the hybrid agent pipeline with tool chaining.
        
        This combines the strengths of:
        1. JSON Mode for structured function calling
        2. Tool Chaining for multi-step reasoning
        3. Dedicated Formatting LLM for high-quality responses
        
        Returns:
            Tuple containing:
            - The response data (Dict or Response object)
            - Status code (int)
        """
        try:
            # Normalize parameters
            context = context or {}
            
            # Generate a session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Retrieve conversation memory for this session
            memory = self.memory_service.get_conversation_memory(session_id)
            conversation_history = memory.messages.copy()
            
            # Store context in flask g for action execution if it's not already there
            if context and not hasattr(g, 'context'):
                g.context = context
            
            # Store session_id in context
            context['session_id'] = session_id
            
            # Add user message to history
            conversation_history.append({
                "role": "user", 
                "content": user_input
            })
            
            # Update conversation memory with new user message
            self.memory_service.update_conversation_memory(session_id, conversation_history)
            
            # Run the tool chaining process
            result = self._process_with_tool_chaining(user_input, conversation_history, response_format, session_id)
            
            # The result contains both the final response and updated conversation history
            response_data, status_code = result.response.to_http_response()
            
            # Add final assistant response to history
            if hasattr(result.response, 'content'):
                final_history = conversation_history.copy()
                final_history.append({
                    "role": "assistant",
                    "content": result.response.content
                })
                
                # Update conversation memory with the complete conversation
                self.memory_service.update_conversation_memory(session_id, final_history)
                
                # Store tool call history as episodic memory
                if result.tool_calls_history:
                    self.memory_service.store_episodic_memory(
                        session_id=session_id,
                        event_type="tool_calls",
                        content={
                            "original_input": user_input,
                            "tool_calls": [item.__dict__ for item in result.tool_calls_history]
                        }
                    )
            
            return response_data, status_code
            
        except Exception as e:
            logging.error(f"Error in agent service: {e}", exc_info=True)
            error_response = ErrorResponse("Failed to process request", str(e))
            response_data, status_code = error_response.to_http_response()
            return response_data, status_code
            
    @dataclass
    class ToolChainResult:
        """Container for the result of tool chaining process"""
        response: ActionResponse
        conversation_history: List[Dict]
        tool_calls_history: List[ToolCallHistoryItem]

    def _process_with_tool_chaining(self, user_input: str, conversation_history: List[Dict], 
                                   response_format: str = "auto",
                                   session_id: str = None) -> ToolChainResult:
        """
        Core tool chaining implementation that handles multiple sequential tool calls.
        
        Args:
            user_input: The original user input
            conversation_history: The conversation history including the latest user input
            response_format: The desired response format
            
        Returns:
            ToolChainResult: Container with final response and updated conversation
        """
        # Initialize tracking variables
        tool_calls_history = []
        iterations = 0
        current_input = user_input
        current_history = conversation_history.copy()
        
        # Tool chaining loop
        while iterations < self.max_tool_calls:
            iterations += 1
            logging.info(f"Tool chaining iteration {iterations}/{self.max_tool_calls}")
            
            # Make a single tool selection call and execution
            selection_response = self._perform_tool_selection_stage(
                user_input=current_input,
                conversation_history=current_history,
                response_format=response_format,
                tool_calls_history=tool_calls_history
            )
            
            # Case 1: If it's a direct response or error, return immediately
            if not selection_response.requires_second_ai_call or selection_response.response_type == "error":
                logging.info(f"Tool chain ended with direct response after {iterations} iterations")
                return self.ToolChainResult(
                    response=selection_response,
                    conversation_history=current_history, 
                    tool_calls_history=tool_calls_history
                )
            
            # Case 2: It's a tool call response - extract details
            tool_call = selection_response.tool_call
            action = selection_response.action
            tool_result = selection_response.result
            
            # Add to tool calls history
            tool_calls_history.append(ToolCallHistoryItem(
                tool_name=tool_call.function.name,
                tool_args=json.loads(tool_call.function.arguments),
                tool_result=self._get_result_as_string(tool_result)
            ))
            
            # Update conversation history with this tool call
            current_history = self._add_tool_interaction_to_messages(
                current_history, 
                tool_call, 
                self._get_result_as_string(tool_result)
            )
            
            # Evaluate if we need more tool calls
            needs_more_tools, next_input = self._evaluate_need_for_more_tools(
                tool_calls_history=tool_calls_history,
                original_input=user_input,
                conversation_history=current_history
            )
            
            if not needs_more_tools:
                logging.info(f"Tool chain complete after {iterations} iterations - proceeding to response generation")
                break
                
            # Update for next iteration
            current_input = next_input
        
        # After tool chain completes, generate final response
        final_response = self._perform_response_generation_stage(
            action=selection_response.action,
            messages=current_history,
            tool_calls_history=tool_calls_history,
            original_input=user_input
        )
        
        return self.ToolChainResult(
            response=final_response,
            conversation_history=current_history,
            tool_calls_history=tool_calls_history
        )
    
    def _perform_tool_selection_stage(self, user_input: str, conversation_history: List[Dict], 
                                     response_format: str = "auto", 
                                     tool_calls_history: List[ToolCallHistoryItem] = None) -> ActionResponse:
        """
        Enhanced tool selection stage that includes tool chaining context
        """
        # Prepare prompt for tool selection with tool call history
        messages = self._prepare_tool_selection_prompt(
            user_input=user_input, 
            conversation_history=conversation_history,
            tool_calls_history=tool_calls_history or []
        )
        
        # Get available tools
        tools = self._get_available_tools()
        
        # Make AI call for tool selection
        try:
            response = self._make_tool_selection_call(messages, tools)
        except Exception as e:
            logging.error(f"Tool selection failed: {e}")
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
        
        # Get context from Flask g if available
        context = getattr(g, 'context', {})
        # Check if user is admin
        is_admin = bool(context.get('IS_ADMIN', False))
        
        # Get the action from registry with proper admin status
        action = registry.get_action(function_name, is_admin)
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
            return ImageResponse(action_result)
        
        # Check for tuple with Response
        if isinstance(action_result, tuple) and len(action_result) == 2:
            response_obj, status_code = action_result
            if isinstance(response_obj, Response) and response_obj.mimetype == "image/png":
                return ImageResponse(response_obj, status_code=status_code)
                
        # For all other cases, return tool execution response
        return ToolExecutionResponse(tool_call, action, action_result, messages)

    def _evaluate_need_for_more_tools(self, tool_calls_history: List[ToolCallHistoryItem], 
                                      original_input: str,
                                      conversation_history: List[Dict]) -> Tuple[bool, str]:
        """
        Determines if more tool calls are needed based on the current state.
        A tool-agnostic implementation that relies on LLM reasoning.
        
        Args:
            tool_calls_history: History of previous tool calls
            original_input: The original user input
            conversation_history: Current conversation history
            
        Returns:
            Tuple[bool, str]: (needs_more_tools, next_input_if_needed)
        """
        # If we've reached the maximum number of tool calls, stop
        if len(tool_calls_history) >= self.max_tool_calls:
            logging.info(f"Reached maximum tool call limit ({self.max_tool_calls})")
            return False, ""

        # If the last tool call was unsuccessful, stop to prevent error loops
        if tool_calls_history and "error" in tool_calls_history[-1].tool_result.lower():
            logging.info("Last tool call had an error - stopping tool chain")
            return False, ""
       
        # Make a dedicated AI call to determine if more tools are needed
        messages = [
            {
                "role": "system", 
                "content": self.prompt_service.generate_tool_evaluation_prompt()
            },
            {
                "role": "user", 
                "content": f"ORIGINAL USER REQUEST: {original_input}\n\n"
                           f"TOOL CALL HISTORY ({len(tool_calls_history)}):\n" + 
                           "\n".join([
                               f"{i+1}. Tool: {item.tool_name}\n   Args: {json.dumps(item.tool_args)}\n   Result: {item.tool_result[:150]}..." 
                               for i, item in enumerate(tool_calls_history)
                           ])
            }
        ]
        
        try:
            # Using a lower temperature for more consistent decision-making
            decision_response = self.openai_gateway.get_completion(messages, temperature=0.1)
            decision_text = decision_response.choices[0].message.content.strip()
            
            logging.debug(f"Tool chain evaluation response: {decision_text}")
            
            if decision_text.startswith("COMPLETE:"):
                logging.info(f"Tool chain evaluation: Complete - {decision_text[9:].strip()}")
                return False, ""
            elif decision_text.startswith("MORE_TOOLS_NEEDED:"):
                # Extract the reasoning part after MORE_TOOLS_NEEDED
                next_input = decision_text[17:].strip()
                logging.info(f"Tool chain evaluation: More tools needed - {next_input}")
                return True, next_input
            else:
                logging.warning(f"Unclear tool chain evaluation result: {decision_text}")
                # Default to ending the chain if the response is unclear
                return False, ""
                
        except Exception as e:
            logging.error(f"Error in tool chain evaluation: {e}")
            return False, ""

    def _prepare_tool_selection_prompt(self, user_input: str, conversation_history: List[Dict], 
                                      tool_calls_history: List[ToolCallHistoryItem] = None) -> List[Dict]:
        """Prepares the prompt for tool selection with tool chaining context"""
        # Use the new enhanced PromptService method that incorporates tool chain context
        return self.prompt_service.generate_tool_selection_prompt_with_context(
            user_input=user_input, 
            conversation_history=conversation_history,
            tool_calls_history=tool_calls_history
        )
    
    def _get_available_tools(self) -> List[Dict]:
        """Gets available tools from the registry based on admin status"""
        # Get context from Flask g if available
        context = getattr(g, 'context', {})
        # Check if user is admin
        is_admin = bool(context.get('IS_ADMIN', False))
        
        # Get tools appropriate for the user's admin status
        return registry.get_tools_for_openai(is_admin=is_admin)
    
    def _make_tool_selection_call(self, messages: List[Dict], tools: List[Dict]) -> Any:
        """Makes the AI call for tool selection"""
        # Using tool_choice instead of function_call to match the OpenAIGateway implementation
        response = self.openai_gateway.get_completion(messages, tools, tool_choice="auto")
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
    
    def _perform_response_generation_stage(self, action: Any = None, messages: List[Dict] = None, 
                                          tool_calls_history: List[ToolCallHistoryItem] = None,
                                          original_input: str = None, 
                                          tool_execution_response: ToolExecutionResponse = None) -> ActionResponse:
        """
        Enhanced response generation stage that works with either a single tool execution
        or the results of a tool chaining sequence.
        
        Args:
            action: The last action executed (optional)
            messages: Updated conversation history messages (optional) 
            tool_calls_history: History of all tool calls in the sequence (optional)
            original_input: Original user input (optional)
            tool_execution_response: Single tool execution response from previous code path (optional)
            
        Returns:
            ActionResponse: Final response to send to the user
        """
        # Handle backward compatibility with the old method signature
        if tool_execution_response:
            # Extract from the single tool execution response
            action = tool_execution_response.action
            messages = tool_execution_response.messages
            tool_result = self._get_result_as_string(tool_execution_response.result)
            
            # Update conversation with single tool interaction
            messages = self._add_tool_interaction_to_messages(
                tool_execution_response.messages, 
                tool_execution_response.tool_call, 
                tool_result
            )
        
        # Prepare final response prompt using the PromptService - this preserves all context relevance instructions
        final_response_messages = self.prompt_service.generate_final_response_prompt_with_context(
            messages=messages, 
            action=action, 
            tool_calls_history=tool_calls_history,
            original_input=original_input
        )
        
        # Make final AI call
        try:
            logging.info("Making AI call for final response generation")
            final_ai_response = self.openai_gateway.get_completion(final_response_messages)
            logging.info("Final response generation complete")
            
            # Parse the content for conversation end marker if present
            content = final_ai_response.choices[0].message.content
            is_conversation_over = False
            
            # Log the raw response content
            logging.debug(f"Final response raw content: {content}")
            
            # Check for JSON with is_conversation_over flag
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    response_json = json.loads(content)
                    logging.debug(f"Successfully parsed JSON from response: {response_json}")
                    
                    if 'is_conversation_over' in response_json:
                        is_conversation_over = bool(response_json.get('is_conversation_over'))
                        logging.info(f"Set conversation_over flag to: {is_conversation_over}")
                    
                    if 'message' in response_json:
                        content = response_json.get('message')
                        logging.debug(f"Extracted message from JSON: {content}")
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse response as JSON: {e}")
            
            # Create text response
            response = TextResponse(content)
            if is_conversation_over:
                response.mark_conversation_over()
                
            return response
            
        except Exception as e:
            logging.error(f"Error in final response generation: {e}")
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
            
            # Use base prompt from PromptService
            base_prompt = self.prompt_service.get_base_system_prompt()
            
            # Add RAG-specific instructions
            rag_prompt = (
                f"{base_prompt}\n\n"
                "RAG QUERY INSTRUCTIONS:\n"
                "- Use ONLY the provided context to answer the question\n"
                "- Be concise but thorough in your response\n"
                "- If the context doesn't fully answer the question, be honest about what you don't know\n"
                "- Do not make up information or use your general knowledge to fill gaps\n"
                "- Focus on addressing the specific query using only the context provided\n"
                "- Format your response in a conversational, helpful tone\n"
                "- Use natural language date formatting (today, tomorrow, next Monday) in your responses\n"
            )
            
            # Prepare prompt for LLM
            messages = [
                {"role": "system", "content": rag_prompt},
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