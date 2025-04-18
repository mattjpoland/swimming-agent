from flask import jsonify, send_file
from src.agent.base import AgentAction
from src.domain.services.membershipService import get_barcode_id_action
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
    
    @property
    def prompt_instructions(self):
        return (
                "If the user asks for their membership barcode or anything related to "
                "accessing the facility with their membership, use the get_membership_barcode function. "        )
    
    @property
    def response_format_instructions(self):
        return (
            ""
        )
    
    def get_tool_definition(self):
        """
        Get the tool definition for OpenAI API.
        This is required for the function calling API.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def execute(self, arguments, context, user_input, **kwargs):
        """Execute the barcode generation action."""
        try:
            # Import here to avoid circular imports
            import barcode
            from barcode.writer import ImageWriter
            import io
            from flask import send_file, jsonify
            from src.domain.services.membershipService import get_barcode_id_action
            
            # Log barcode library version for debugging
            import pkg_resources
            barcode_version = pkg_resources.get_distribution("python-barcode").version
            logging.info(f"Using python-barcode version: {barcode_version}")
            
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
            
            # Log the original barcode ID for verification
            logging.info(f"Generating barcode for ID: {barcode_id}")
            
            # Create the ImageWriter instance without options parameter
            writer = ImageWriter()
            
            # Set writer attributes individually (for older versions)
            # These are common settings that might be supported
            writer.quiet_zone = 2.5
            writer.text = True  # Enable text rendering
            
            # Generate the barcode image using Code 39 without checksum
            barcode_class = barcode.get_barcode_class('code39')
            
            # Try with add_checksum parameter first
            try:
                barcode_format = barcode_class(barcode_id, writer=writer, add_checksum=False)
            except TypeError:
                # Fallback for older versions that don't support add_checksum parameter
                barcode_format = barcode_class(barcode_id, writer=writer)
                # Try to set the property after initialization
                try:
                    barcode_format.add_checksum = False
                except (AttributeError, TypeError):
                    logging.warning("Could not disable checksum through property, using default behavior")
            
            # Verify the encoded data doesn't have an added checksum
            try:
                encoded_data = barcode_format.get_fullcode()
                logging.info(f"Encoded barcode data: {encoded_data}")
                
                # Validate that no checksum was added
                if encoded_data != barcode_id:
                    logging.warning(f"WARNING: Encoded data ({encoded_data}) doesn't match original ID ({barcode_id})")
            except (AttributeError, TypeError):
                logging.warning("Could not verify encoded data, continuing with generation")
            
            # Generate the barcode image
            barcode_image = io.BytesIO()
            barcode_format.write(barcode_image)
            barcode_image.seek(0)
            
            # Return the barcode image as a Flask Response
            return send_file(barcode_image, mimetype="image/png")
            
        except Exception as e:
            logging.exception(f"Error generating barcode: {str(e)}")
            return jsonify({"message": "I encountered an error while generating your barcode. Please try again later.", "status": "error"}), 500