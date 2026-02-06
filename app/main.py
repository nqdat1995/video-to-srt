"""Main FastAPI application"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress PaddleOCR debug logs FIRST (before any imports)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONWARNINGS'] = 'ignore'

# Disable oneDNN to avoid PIR attribute issues on Windows
os.environ['PADDLE_DISABLE_FAST_MATH'] = '1'
os.environ['PADDLE_PYCUDA_CACHE_DIR'] = ''
os.environ['FLAGS_use_mkldnn'] = '0'

# Configure logging to suppress DEBUG logs from paddleocr
logging.basicConfig(level=logging.WARNING)
for logger_name in ['paddleocr', 'paddle', 'paddlex', 'PIL', 'cv2', 'urllib3']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import settings

# Create FastAPI app
app = FastAPI(
   title=settings.APP_NAME,
   version=settings.VERSION,
   description=settings.DESCRIPTION
)

# Add CORS middleware
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

# Include routes
app.include_router(router)


if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)