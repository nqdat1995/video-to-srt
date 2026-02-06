"""Logging configuration for the application"""

import logging
import os


def configure_logging(level: str = "WARNING") -> None:
    """
    Configure logging to suppress debug logs from paddleocr and dependencies
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Parse logging level
    log_level = getattr(logging, level.upper(), logging.WARNING)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Suppress verbose loggers regardless of root level
    # These are known to be chatty during initialization
    verbose_loggers = [
        'paddleocr',
        'paddle',
        'paddlex',
        'paddlepaddle',
        'PIL',
        'cv2',
        'urllib3',
        'matplotlib',
    ]
    
    for logger_name in verbose_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        # Disable propagation to parent logger
        logger.propagate = False


def suppress_paddle_debug_output() -> None:
    """
    Suppress PaddleOCR and PaddlePaddle debug output via environment variables
    """
    # TensorFlow logging
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0=all, 1=info, 2=warning, 3=error
    
    # Suppress Python warnings
    os.environ['PYTHONWARNINGS'] = 'ignore'
    
    # Optional: Suppress oneDNN info messages
    os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '3'
    
    # Configure logging
    configure_logging("WARNING")
