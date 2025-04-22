import logging
import os
from typing import Dict, Any, Optional

class LoggingService:
    """
    Service for managing logging configuration across the application.
    Provides methods to configure logging levels for different components.
    """
    
    # Default logging levels
    DEFAULT_CONFIG = {
        "root": logging.INFO,
        "openai": logging.WARNING,
        "httpcore": logging.WARNING,
        "urllib3": logging.WARNING,
        "httpx": logging.WARNING,
        "agent": logging.INFO,
        "tools": logging.INFO
    }
    
    # Predefined configurations
    PRESET_CONFIGS = {
        "verbose": {
            "root": logging.DEBUG,
            "openai": logging.DEBUG,
            "httpcore": logging.INFO,
            "urllib3": logging.INFO,
            "httpx": logging.INFO,
            "agent": logging.DEBUG,
            "tools": logging.DEBUG
        },
        "normal": DEFAULT_CONFIG,
        "quiet": {
            "root": logging.WARNING,
            "openai": logging.ERROR,
            "httpcore": logging.ERROR,
            "urllib3": logging.ERROR,
            "httpx": logging.ERROR,
            "agent": logging.INFO,
            "tools": logging.WARNING
        },
        "dev": {
            "root": logging.INFO,
            "openai": logging.WARNING,
            "httpcore": logging.ERROR,
            "urllib3": logging.WARNING,
            "httpx": logging.WARNING,
            "agent": logging.DEBUG,
            "tools": logging.INFO
        }
    }
    
    @classmethod
    def configure(cls, config: Optional[Dict[str, int]] = None, 
                 preset: Optional[str] = None,
                 log_file: Optional[str] = None):
        """
        Configure logging levels for all components.
        
        Args:
            config: Custom logging level configuration
            preset: Name of predefined configuration preset ('verbose', 'normal', 'quiet', 'dev')
            log_file: Optional file path to write logs to
        """
        # Start with the default configuration
        effective_config = cls.DEFAULT_CONFIG.copy()
        
        # Apply preset if specified
        if preset and preset in cls.PRESET_CONFIGS:
            effective_config.update(cls.PRESET_CONFIGS[preset])
        
        # Apply custom config if provided (overrides preset)
        if config:
            effective_config.update(config)
            
        # Configure the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(effective_config.get("root", logging.INFO))
        
        # Clear existing handlers to avoid duplicate logs
        if root_logger.handlers:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(effective_config.get("root", logging.INFO))
        
        # Create formatter
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        console_handler.setFormatter(formatter)
        
        # Add console handler to root logger
        root_logger.addHandler(console_handler)
        
        # Add file handler if log_file is specified
        if log_file:
            # Ensure directory exists
            log_dir = os.path.dirname(os.path.abspath(log_file))
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        for logger_name, level in effective_config.items():
            if logger_name != "root":
                logging.getLogger(logger_name).setLevel(level)
        
        # Log the configuration
        logging.info(f"Logging configured with {'preset: ' + preset if preset else 'custom configuration'}")
        if log_file:
            logging.info(f"Logging to file: {log_file}")
    
    @classmethod
    def set_level(cls, logger_name: str, level: int):
        """
        Set the logging level for a specific logger.
        
        Args:
            logger_name: Name of the logger (e.g., 'openai', 'httpcore')
            level: Logging level (e.g., logging.INFO, logging.DEBUG)
        """
        logging.getLogger(logger_name).setLevel(level)
        logging.info(f"Set logging level for '{logger_name}' to {logging.getLevelName(level)}")
        
    @classmethod
    def get_level(cls, logger_name: str) -> int:
        """
        Get the current level for a specific logger.
        
        Args:
            logger_name: Name of the logger
            
        Returns:
            int: The current logging level
        """
        return logging.getLogger(logger_name).level