from flask import jsonify, send_file
from src.agent.base import AgentAction
from src.api.logic.membershipService import get_barcode_id_action
import logging
import io

class BarcodeAction(AgentAction):
    @property
    def name(self):
        return "get_membership_barcode"
    
    @property
    def description(self):
        return "Generate and retrieve the user's membership barcode image."
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {},
            "required": []  # No parameters required for barcode generation
        }
    
    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the barcode generation action."""
        try:
            # Import here to avoid circular imports
            import barcode
            from barcode.writer import ImageWriter
            
            # Get the barcode ID using the membership service
            response, status_code = get_barcode_id_action(context)
            
            # If there was an error, return a friendly message
            if status_code != 200:
                return jsonify({
                    "message": "Sorry, I couldn't retrieve your membership barcode. Please make sure you're logged in or contact support if the issue persists.", 
                    "status": "error"
                }), status_code
            
            # Extract the barcode ID from the response
            barcode_id = response.get("barcode_id")
            
            # Generate the barcode image using Code 39 without checksum
            barcode_class = barcode.get_barcode_class('code39')
            barcode_format = barcode_class(barcode_id, writer=ImageWriter())
            barcode_format.add_checksum = False  # Disable the checksum - critical for compatibility
            barcode_image = io.BytesIO()
            barcode_format.write(barcode_image)
            barcode_image.seek(0)
            
            # Return the barcode image with explanatory headers
            response_obj = send_file(barcode_image, mimetype="image/png")
            response_obj.headers["X-Barcode-ID"] = barcode_id
            response_obj.headers["X-Response-Type"] = "barcode"
            return response_obj
            
        except Exception as e:
            return self.handle_error(e, "I encountered an error while generating your barcode. Please try again later.")