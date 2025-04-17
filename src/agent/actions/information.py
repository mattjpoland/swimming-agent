from src.agent.base import AgentAction
from src.utils.rag_querying import query_rag
import logging

class InformationAction(AgentAction):
    @property
    def name(self):
        return "get_pool_information"
    
    @property
    def description(self):
        return "Retrieve information about pool facilities, policies, or schedules using RAG"
    
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
    
    @property
    def prompt_instructions(self):
        return (
            "Use this function to answer questions about pool information, policies, "
            "facility details, or general schedules. Examples: pool hours, facility rules, "
            "swim lesson information, pool dimensions, etc."
        )

    def execute(self, arguments, context, user_input, **kwargs):
        try:
            # Query the RAG system
            results = query_rag(arguments["question"])
            
            if not results:
                return {
                    "message": "I'm sorry, I couldn't find specific information about that. Please contact the facility directly for the most accurate information.",
                    "status": "no_results"
                }
            
            # Combine the relevant chunks into context
            context_text = "\n".join([chunk["text"] for chunk in results])
            
            # Use OpenAI to generate a natural response using the retrieved context
            messages = [
                {"role": "system", "content": (
                    "You are a helpful assistant for a swimming facility. "
                    "Use the provided context to answer questions accurately and concisely. "
                    "If the context doesn't fully answer the question, be honest about what you don't know."
                )},
                {"role": "user", "content": f"Using this context:\n\n{context_text}\n\nAnswer this question: {arguments['question']}"}
            ]
            
            response = self.openai_gateway.get_completion(messages)
            answer = response.choices[0].message.content
            
            return {
                "message": answer,
                "status": "success",
                "source_count": len(results)
            }
            
        except Exception as e:
            logging.error(f"Error in InformationAction: {e}")
            return {
                "message": "I apologize, but I encountered an error while retrieving that information.",
                "status": "error",
                "error": str(e)
            }