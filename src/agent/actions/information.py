from src.agent.base import AgentAction
from src.agent.gateways.openAIGateway import OpenAIGateway
from src.domain.services.ragQueryingService import query_rag
import logging

class InformationAction(AgentAction):
    def __init__(self):
        super().__init__()
        self.openai_gateway = OpenAIGateway()

    @property
    def name(self):
        return "get_pool_information"

    @property
    def description(self):
        return "Retrieve information about pool facilities, policies, or schedules using RAG"
    
    @property
    def prompt_instructions(self):
        return """
When answering questions about pool hours or schedules:
- Use the current date context provided in the system prompt
- Reference specific days of the week when relevant
- Clearly indicate if the information is date-dependent
- Format pool hours in 12-hour time (e.g., 7:00 AM - 8:00 PM)
- Note any special conditions or exceptions
"""

    @property
    def response_format_instructions(self):
        return (
            "Format your response as a helpful, conversational answer about the pool facilities:\n"
            "1. Start with a direct answer to the user's question\n"
            "2. Format hours in 12-hour time (e.g., 7:00 AM - 8:00 PM)\n"
            "3. Highlight important policies or restrictions if relevant\n"
            "4. When sharing pool hours or schedules, organize them in a clear, scannable format\n"
            "5. If the information varies by day, clearly indicate which days apply to which hours\n"
            "6. If the requested information isn't available in the context, acknowledge the limitation politely"
        )

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user's question about pool information"
                }
            },
            "required": ["question"]
        }

    def execute(self, arguments, context, user_input, **kwargs):
        try:
            question = arguments.get("question")
            if not question:
                raise ValueError("Question is required")

            results = query_rag(question)
            if not results:
                return {
                    "message": "No information found",
                    "status": "no_results"
                }

            # Combine context from top matches
            context_text = "\n".join([chunk["text"] for chunk in results])
            
            # Get raw factual information
            messages = [
                {"role": "system", "content": """
Extract only the relevant pool information from the context:
- Include specific hours and conditions
- Keep it factual without conversational elements
- Include date-specific details if relevant
- Structure data in a clear, parseable format
"""},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
            ]

            response = self.openai_gateway.get_completion(messages)
            
            return {
                "raw_info": response.choices[0].message.content,
                "status": "success",
                "sources": [r["source"] for r in results],
                "confidence": max(r["similarity"] for r in results),
                "metadata": {
                    "question_type": "pool_hours" if "hours" in question.lower() else "general",
                    "sources_used": list(set(r["source"] for r in results))
                }
            }
                
        except Exception as e:
            logging.error(f"Error in InformationAction: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }