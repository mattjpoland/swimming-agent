import io
import logging
import barcode
from barcode.writer import ImageWriter

def generate_barcode_image(barcode_id):
    """
    Generate a barcode image for the given barcode ID using Code 39.

    Args:
        barcode_id (str): The ID to encode in the barcode.

    Returns:
        BytesIO: A BytesIO object containing the barcode image.
    """
    try:
        # Get the barcode class for Code 39
        barcode_class = barcode.get_barcode_class('code39')

        # Create the barcode writer
        writer = ImageWriter()

        # Generate the barcode
        barcode_format = barcode_class(barcode_id, writer=writer, add_checksum=False)

        # Create an in-memory image
        barcode_image = io.BytesIO()
        barcode_format.write(barcode_image)
        barcode_image.seek(0)

        return barcode_image

    except Exception as e:
        logging.exception(f"Error generating barcode: {str(e)}")
        raise RuntimeError(f"Failed to generate barcode: {str(e)}")