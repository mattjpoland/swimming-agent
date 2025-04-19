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
    - Private AI-1 helper methods 
    - Private AI-2 helper methods
    - Shared helper methods
    """
    
    # =========================================================================
    # PUBLIC AI-1 METHODS (TOOL SELECTION)
    # =========================================================================
    
    def generate_initial_tool_selection_prompt(self, user_input: str, conversation_history: List[Dict] = None) -> List[Dict]:
        """
        Builds the messages array for AI-1 (tool selection) with system prompt and conversation history.
        This is the main entry point for AI-1 prompt generation.
        
        [AI 1 Prompts called by AgentService]
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
        
        # Add conversation history
        if conversation_history:
            for message in conversation_history:
                role = message.get("role", "user")
                content = message.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
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