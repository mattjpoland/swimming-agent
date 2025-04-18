"""
Special response classes for non-text responses like images and files.
"""
from typing import Dict, Any, Tuple, Optional
import io
from flask import Response
from src.agent.responses.base import ActionResponse


class ImageResponse(ActionResponse):
    """
    Image response for returning image data.
    """
    
    def __init__(self, image_data_or_response, mimetype: str = "image/png", status_code: int = 200):
        """
        Initialize an image response.
        
        Args:
            image_data_or_response: Either raw image binary data or a Flask Response object
            mimetype: Image MIME type
            status_code: HTTP status code
        """
        self.status_code = status_code
        
        # Handle both raw bytes and Flask Response objects safely
        if isinstance(image_data_or_response, Response):
            # Store the original response instead of trying to extract data
            self._flask_response = image_data_or_response
            self.mimetype = image_data_or_response.mimetype or mimetype
        else:
            # It's raw bytes
            self.image_data = image_data_or_response
            self.mimetype = mimetype
            self._flask_response = Response(image_data_or_response, mimetype=mimetype)
    
    @property
    def response_type(self) -> str:
        return "image"
    
    @property
    def requires_second_ai_call(self) -> bool:
        """Images don't need a second AI call."""
        return False
    
    def to_http_response(self) -> Tuple[Response, int]:
        return self._flask_response, self.status_code
    
    def to_string(self) -> str:
        return f"[Image: {self.mimetype}]"


class FileResponse(ActionResponse):
    """
    File response for returning downloadable files.
    """
    
    def __init__(self, file_data_or_response, filename: str, 
                 mimetype: Optional[str] = None, status_code: int = 200):
        """
        Initialize a file response.
        
        Args:
            file_data_or_response: Either raw file binary data or a Flask Response
            filename: Name of the file for download
            mimetype: File MIME type
            status_code: HTTP status code
        """
        self.filename = filename
        self.status_code = status_code
        
        # Handle both bytes and Response objects
        if isinstance(file_data_or_response, Response):
            self._flask_response = file_data_or_response
            self.mimetype = file_data_or_response.mimetype or mimetype
            
            # Add Content-Disposition header if not already present
            if 'Content-Disposition' not in self._flask_response.headers:
                self._flask_response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        else:
            # It's raw bytes
            self.file_data = file_data_or_response
            self.mimetype = mimetype
            self._flask_response = Response(file_data_or_response, mimetype=mimetype)
            self._flask_response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    
    @property
    def response_type(self) -> str:
        return "file"
    
    @property
    def requires_second_ai_call(self) -> bool:
        """Files don't need a second AI call."""
        return False
    
    def to_http_response(self) -> Tuple[Response, int]:
        return self._flask_response, self.status_code
    
    def to_string(self) -> str:
        return f"[File: {self.filename}]"