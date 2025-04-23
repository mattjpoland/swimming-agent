from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any, Optional
from src.agent.registry import registry

class PromptService:
    """
    Centralizes the management of prompts for the agent system.
    Responsible for creating common prompt components, combining with action-specific
    prompts, and formatting responses according to specific requirements.
    
    The class follows this organizational structure:
    - Public AI-1 methods (tool selection)
    - Public AI-2 methods (response formatting)
    - Public Tool Chaining methods
    - Private AI-1 helper methods 
    - Private AI-2 helper methods
    - Shared helper methods
    """
    
    # =========================================================================
    # PUBLIC AI-1 METHODS (TOOL SELECTION)
    # =========================================================================
    
    def generate_initial_tool_selection_prompt(self, user_input: str, conversation_history=None) -> List[Dict]:
        """
        Builds the messages array for AI-1 (tool selection) with system prompt and conversation history.
        This is the main entry point for AI-1 prompt generation.
        
        [AI 1 Prompts called by AgentService]
        
        Args:
            user_input: The user's current input
            conversation_history: Conversation history (provided by memory service)
        """
        # Build system prompt directly
        system_prompt = self._get_base_identity_prompt()
        system_prompt += self._get_tool_selection_prompt()
        system_prompt += self._get_action_selection_prompts()
        system_prompt += (
            "VERY IMPORTANT - CONVERSATION MANAGEMENT INSTRUCTIONS:\n"
            "If a tool is not selected, format your response as a JSON object with these fields:\n"
            "{\n"
            "  \"is_conversation_over\": boolean,\n"
            "  \"message\": \"Your natural language response here\"\n"
            "}\n\n"
            "Follow these specific rules to determine the value of \"is_conversation_over\":\n"
            "1. Set to true only when user indicates they're finished (thanks, bye, that's all).\n"
            "2. For all other responses, set to false.\n"
        )
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for message in conversation_history:
                if not isinstance(message, dict):
                    continue  # Skip non-dict messages
                    
                # Extract role and content safely
                role = message.get("role", "user") if hasattr(message, "get") else "user"
                content = message.get("content", "") if hasattr(message, "get") else str(message)
                
                # Handle tool calls
                tool_calls = message.get("tool_calls", None)
                tool_call_id = message.get("tool_call_id", None)
                
                if role in ["user", "assistant", "tool"] and (content or tool_calls):
                    if tool_calls:
                        # Format tool call message
                        msg = {"role": role, "content": content, "tool_calls": tool_calls}
                        messages.append(msg)
                    elif tool_call_id:
                        # Format tool response message
                        msg = {"role": role, "content": content, "tool_call_id": tool_call_id}
                        messages.append(msg)
                    else:
                        # Format normal message
                        messages.append({"role": role, "content": content})
        
        return messages
    
    # =========================================================================
    # PUBLIC AI-2 METHODS (RESPONSE FORMATTING)
    # =========================================================================
    
    def generate_final_response_prompt(self, messages: List[Dict], action: Any) -> List[Dict]:
        """
        Adds action-specific response formatting instructions for AI-2 (final response).
        This is the main entry point for AI-2 prompt enhancement.
        
        [AI 2 Prompts called by AgentService]
        """
        # Create a new system message with the action's response formatting instructions
        # Start with base identity for context
        prompt = self._get_base_identity_prompt()

        # Add common response formatting
        prompt += (
            "\n\nRESPONSE FORMATTING INSTRUCTIONS:\n"
            "- Use natural, conversational language\n"
            "- Be concise but complete\n"
            "- Format dates in a user-friendly way\n"
            "- When reporting data from tools, only include information actually provided in the tool response\n"
            "- Do not invent, hallucinate, or generate fictional data\n"
        )
        
        # Add humanized date format instructions
        prompt += (
            "\nFormat dates in a user-friendly way:\n"
            "- Use 'today', 'tomorrow', 'yesterday' when appropriate\n"
            "- Use day names ('Monday', 'next Tuesday') for dates within a week\n"
            "- Use 'the 5th', 'May 5th' for dates slightly farther out\n"
        )
        
        if action and hasattr(action, 'response_format_instructions'):            
            # Add the action-specific formatting instructions
            prompt += f"{action.response_format_instructions}\n\n"
            
        prompt += (
            "VERY IMPORTANT - CONVERSATION MANAGEMENT INSTRUCTIONS:\n"
            "Always format your response as a JSON object with these fields:\n"
            "{\n"
            "  \"is_conversation_over\": boolean,\n"
            "  \"message\": \"Your natural language response here\"\n"
            "}\n\n"
            "Follow these specific rules to determine the value of \"is_conversation_over\":\n"
            "1. Set to true only when user indicates they're finished (thanks, bye, that's all).\n"
            "2. For all other responses, set to false.\n"
        )
        
        # Add the new system message for formatting guidance
        messages.append({
            "role": "system",
            "content": prompt
        })
        
        return messages
    
    def generate_final_response_prompt_with_context(self, messages: List[Dict], action: Any = None,
                                                   tool_calls_history: List = None,
                                                   original_input: str = None) -> List[Dict]:
        """
        Enhanced prompt preparation for the final response generation
        that includes tool chain context when available and improved context relevance
        
        Args:
            messages: The conversation messages
            action: The last action executed (optional)
            tool_calls_history: History of all tool calls in the sequence (optional)
            original_input: Original user input (optional)
            
        Returns:
            List[Dict]: Enhanced messages with tool chain context
        """
        # Get base prompt
        final_messages = self.generate_final_response_prompt(messages, action)
        
        # Add tool chain context if available with improved context management
        if tool_calls_history and len(tool_calls_history) > 0:
            # Find the last system message to augment
            for i, msg in enumerate(final_messages):
                if msg["role"] == "system":
                    # Add context management instructions specific to the tool chain
                    context_instructions = "\n\nCONTEXT RELEVANCE INSTRUCTIONS FOR FINAL RESPONSE:"
                    context_instructions += "\n- Focus ONLY on the most recent user request and relevant tool results"
                    context_instructions += "\n- For time-based queries, only mention the MOST RECENT time reference (today/tomorrow/Thursday)"
                    context_instructions += "\n- When a user has changed their preferred day/time, COMPLETELY IGNORE information about previous days/times"
                    context_instructions += "\n- ONLY provide information about the newly requested day/time"
                    context_instructions += "\n- Do NOT compare with previously mentioned times unless explicitly asked"
                    context_instructions += "\n- Format your response to focus exclusively on the new time period requested"
                    
                    # Add brief tool history summary focused on most relevant results
                    if len(tool_calls_history) > 1:
                        context_instructions += "\n\nThis request required multiple steps to fulfill:"
                        
                        # Find the most relevant tool call (usually the last one)
                        last_tool = tool_calls_history[-1]
                        most_relevant = f"\nMOST RELEVANT RESULT: {last_tool.tool_name}: {last_tool.tool_result[:150]}..."
                        context_instructions += most_relevant
                    else:
                        # Single tool call
                        context_instructions += f"\n\nRequest fulfilled with: {tool_calls_history[0].tool_name}"
                    
                    final_messages[i]["content"] += context_instructions
                    break
        
        # If this is a follow-up to a time-based query, add special handling instructions
        if original_input and any(word in original_input.lower() for word in ["how about", "what about", "instead", "tomorrow", "thursday", "friday", "monday", "tuesday", "wednesday", "saturday", "sunday"]):
            for i, msg in enumerate(final_messages):
                if msg["role"] == "system":
                    time_query_instructions = "\n\nTIME-BASED QUERY HANDLING:"
                    time_query_instructions += "\n- This appears to be a follow-up time query or day change"
                    time_query_instructions += "\n- IMPORTANT: Treat this as a COMPLETE REPLACEMENT of any previous day/time mentioned"
                    time_query_instructions += "\n- ONLY provide information about the newly requested day/time"
                    time_query_instructions += "\n- Do NOT compare with previously mentioned times unless explicitly asked"
                    time_query_instructions += "\n- Format your response to focus exclusively on the new time period requested"
                    
                    final_messages[i]["content"] += time_query_instructions
                    break
        
        return final_messages
    
    # =========================================================================
    # PUBLIC TOOL CHAINING METHODS
    # =========================================================================
    
    def generate_tool_evaluation_prompt(self) -> str:
        """
        Generates prompt instructions specifically for evaluating if more 
        tool calls are needed during tool chaining.
        
        [Tool Chaining Prompt called by AgentService]
        """
        # Start with domain-specific identity
        prompt = (
            "You are a swimming agent coordinator that helps break down user requests into a sequence "
            "of tool calls. Your job is to determine if the user's swimming-related request has been completely "
            "fulfilled by the tools called so far."
            
            "\n\nINSTRUCTIONS:"
            "\n1. Analyze the original user request and the tools that have been called"
            "\n2. Determine if the request is fully satisfied or requires additional tools"
            "\n3. If more tools are needed, identify the next logical step in the sequence"
            "\n4. Consider relationships between data (e.g., dates from one tool may need to be used in another tool)"
            "\n5. Be efficient - if a tool has already provided relevant information to answer the user's question, mark it as complete"
            
            "\n\nCONTEXT RELEVANCE INSTRUCTIONS:"
            "\n- For time-based queries (today/tomorrow/Thursday), focus ONLY on the most recent time reference"
            "\n- When user switches from one day to another (e.g., 'Not today, how about tomorrow?'), completely discard information about the previous day"
            "\n- If user modifies their request to a different time or location, treat it as a replacement of the previous request"
            "\n- Only maintain context that directly contributes to fulfilling the current, most recent user request"
            "\n- Do not accumulate information across different days or time slots unless explicitly requested"
            "\n- If user starts a completely new topic, all previous tool call information should be considered irrelevant"
            
            "\n\nIMPORTANT DOMAIN UNDERSTANDING:"
            "\n- This is a swimming facility, so when users ask about 'appointments', they are always referring to swim lane appointments"
            "\n- An appointment response from the check_appointments tool already provides all needed swimming appointment information"
            "\n- Availability information from check_lane_availability is complete and doesn't need verification"
            "\n- Weather information from get_weather or get_weather_forecast is complete for the day requested"
            
            "\n\nCOMMON COMPLETE SCENARIOS:"
            "\n- When the user asked for appointments and got information about appointments (these are always swim lane appointments)"
            "\n- When the user asked about availability and received availability information"
            "\n- When the user asked about weather and received weather information"
            "\n- When the user's entire question has been directly addressed by the last tool call's result"
            "\n- When the user has switched topics and received a complete answer for the new topic"
            
            "\n\nRESPOND WITH EXACTLY ONE OF THESE OPTIONS:"
            "\n- If the request is complete: 'COMPLETE: <brief explanation>'"
            "\n- If more tools are needed: 'MORE_TOOLS_NEEDED: <specific next step and any context needed>'"
        )
        
        return prompt
    
    # =========================================================================
    # PRIVATE AI-1 HELPER METHODS (TOOL SELECTION)
    # =========================================================================
    
    def _get_tool_selection_prompt(self) -> str:
        """
        Generates prompt instructions specifically for tool selection (AI-1).
        These are general tool selection guidelines, not specific to any action.
        
        [AI 1 Prompts only called by PromptService]
        """
        prompt = "\n\nTOOL SELECTION INSTRUCTIONS:\n"
        
        # Generic tool selection guidance
        prompt += (
            "Select the appropriate tool based on the user's request. "
            "Each tool has specific usage instructions provided by the actions.\n"
        )
        
        # Add date formatting instructions for tool selection
        prompt += (
            "\nWhen determining dates for tool parameters:\n"
            "- Convert natural language dates (tomorrow, next Monday) to YYYY-MM-DD format\n"
            "- Use the date references provided above\n"
        )
        
        return prompt

    def _get_action_selection_prompts(self) -> str:
        """
        Collects all action-specific tool selection instructions.
        These are only relevant for AI-1 (tool selection).
        
        [AI 1 Prompts only called by PromptService]
        """
        prompt = ""
        for action in registry.get_all_actions():
            if hasattr(action, "prompt_instructions"):
                prompt += f"\n{action.prompt_instructions}"
        return prompt
    
    
    # =========================================================================
    # SHARED HELPER METHODS
    # =========================================================================
    
    def _get_base_identity_prompt(self) -> str:
        """
        Generates the base identity prompt with common information and date context.
        This is shared between tool selection (AI-1) and response formatting (AI-2).
        
        [Shared Helper called by AI 1 and AI 2 prompt methods]
        """
        # Use Eastern timezone
        eastern_tz = pytz.timezone('US/Eastern')
        now = datetime.now(eastern_tz)

        # Get today and tomorrow dates in YYYY-MM-DD format
        today_date = now.strftime("%Y-%m-%d")
        tomorrow_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Current day name and tomorrow's day name
        current_day_of_week = now.strftime("%A")
        tomorrow_day_of_week = (now + timedelta(days=1)).strftime("%A")

        # Calculate the dates for the next 7 days with their day names
        next_days = []
        for i in range(2, 8):  # Start from 2 because 0 is today and 1 is tomorrow
            next_day = (now + timedelta(days=i))
            next_days.append({
                "date": next_day.strftime("%Y-%m-%d"),
                "day": next_day.strftime("%A")
            })

        # Start with basic information
        prompt = (
            f"You are a helpful assistant for a swimming facility. "
            f"The current date is {today_date}. "
            "You can assist users with checking swim lane availability, booking lanes, canceling appointments, "
            "and providing weather information.\n\n"
        )

        # Add detailed date and timezone information
        prompt += (
            f"The current date and time in Eastern Time (ET) is {now.strftime('%Y-%m-%d %H:%M %Z')}. "
            f"Today is {current_day_of_week}, {today_date}. "
            f"Tomorrow is {tomorrow_day_of_week}, {tomorrow_date}. "
        )

        # Add next days information
        prompt += "Here are the dates for the upcoming week: "
        for day_info in next_days:
            prompt += f"{day_info['day']} is {day_info['date']}, "
        prompt = prompt.rstrip(", ") + ". "

        return prompt

    def get_base_system_prompt(self) -> str:
        """
        Returns the base system prompt with identity, capabilities, and context management instructions.
        """
        return """You are an AI assistant for the YMCA of Lansing. Your purpose is to help members navigate swimming resources, find information, and make swim-related appointments.

You have access to specialized tools for checking appointment availability, making bookings, handling cancellations, providing facility information, and checking weather conditions.

CONTEXT MANAGEMENT INSTRUCTIONS:
- Carefully analyze conversation history to determine what's relevant to the current query
- For time-based queries (today/tomorrow/Thursday/etc.), focus on the MOST RECENT time reference only
- When user changes their preferred day/time, treat it as a replacement rather than accumulation
- For follow-up questions ("what about X instead?"), maintain relevant context but discard obsolete information
- Don't include outdated or irrelevant information from previous exchanges in your current response
- When gathering parameters across multiple turns, focus only on the specific parameters still needed
- If user starts a completely new topic, previous unrelated context should be disregarded"""