"""Run script for development server"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress PaddleOCR debug logs FIRST (before any imports)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONWARNINGS'] = 'ignore'

# Disable oneDNN to avoid PIR attribute issues (compatibility fix)
# Note: PaddleOCR 2.7.0.3 with PaddlePaddle 3.0.0 requires these flags
os.environ['PADDLE_DISABLE_FAST_MATH'] = '1'
os.environ['PADDLE_PYCUDA_CACHE_DIR'] = ''
os.environ['FLAGS_use_mkldnn'] = '0'  # Disable MKL-DNN backend

# Configure logging to suppress DEBUG logs
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress verbose loggers
for logger_name in ['paddleocr', 'paddle', 'paddlex', 'PIL', 'cv2', 'urllib3']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

import uvicorn
from app.main import app

if __name__ == "__main__":
   uvicorn.run(
       "app.main:app",
       host="0.0.0.0",
       port=8000,
       reload=True,  # Auto-reload on code changes
       log_level="info"
   )
