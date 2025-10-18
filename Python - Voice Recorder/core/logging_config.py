#!/usr/bin/env python3
"""
Centralized logging configuration for Voice Recorder Pro
Provides structured logging with file rotation, multiple handlers, and proper formatting.
Supports both text and JSON logging formats.
"""
import logging
import logging.handlers
from pathlib import Path
import sys

class LoggingConfig:
    """Centralized logging configuration manager"""
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_dir: str = "logs",
                 app_name: str = "VoiceRecorderPro",
                 enable_json: bool = False):
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.enable_json = enable_json
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_logging(self) -> logging.Logger:
        """Configure application-wide logging"""
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # JSON formatter (if enabled)
        json_formatter = None
        if self.enable_json:
            try:
                from .structured_logging import JSONFormatter
                json_formatter = JSONFormatter()
            except ImportError:
                logging.warning("structured_logging module not available, JSON logging disabled")
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.handlers.clear()  # Clear any existing handlers
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.app_name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(simple_formatter)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.app_name}_errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        
        # JSON file handler (if enabled)
        if self.enable_json and json_formatter is not None:
            json_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / f"{self.app_name}_structured.jsonl",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            json_handler.setLevel(self.log_level)
            json_handler.setFormatter(json_formatter)
            root_logger.addHandler(json_handler)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(error_handler)
        
        # Create app logger
        app_logger = logging.getLogger(self.app_name)
        app_logger.info("Logging system initialized")
        
        return app_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f"VoiceRecorderPro.{name}")

# Global logging setup
_logging_config = None

def setup_application_logging(log_level: str = "INFO", enable_json: bool = False) -> logging.Logger:
    """Setup application-wide logging (call once at startup)"""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig(log_level=log_level, enable_json=enable_json)
        return _logging_config.setup_logging()
    return logging.getLogger("VoiceRecorderPro")

def configure_build_logging() -> logging.Logger:
    """Special configuration for build scripts with enhanced console output"""
    setup_application_logging("INFO")
    return get_logger("build")
