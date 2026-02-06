"""Setup script for video-to-srt package"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
   long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
   requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
   name="video-to-srt",
   version="1.1.0",
   author="Your Name",
   author_email="your.email@example.com",
   description="Extract subtitles from video using OCR and convert to SRT",
   long_description=long_description,
   long_description_content_type="text/markdown",
   url="https://github.com/yourusername/video-to-srt",
   packages=find_packages(),
   classifiers=[
       "Development Status :: 4 - Beta",
       "Intended Audience :: Developers",
       "Topic :: Multimedia :: Video",
       "Topic :: Text Processing :: Linguistic",
       "License :: OSI Approved :: MIT License",
       "Programming Language :: Python :: 3",
       "Programming Language :: Python :: 3.8",
       "Programming Language :: Python :: 3.9",
       "Programming Language :: Python :: 3.10",
       "Programming Language :: Python :: 3.11",
       "Programming Language :: Python :: 3.12",
       "Framework :: FastAPI",
       "Operating System :: OS Independent",
   ],
   keywords="video subtitle ocr srt paddleocr fastapi",
   python_requires=">=3.8,<3.13",  # Updated range
   install_requires=requirements,  # Load from requirements.txt
   extras_require={
       "dev": [
           "pytest>=7.0.0",
           "pytest-asyncio>=0.21.0",
           "black>=23.0.0",
           "flake8>=6.0.0",
           "mypy>=1.0.0",
       ],
       "gpu": [
           "paddlepaddle-gpu>=3.2.1,<4.0.0",
       ],
   },
   entry_points={
       "console_scripts": [
           "video-to-srt=run:main",
       ],
   },
   package_data={
       "app": ["*.py"],
   },
   include_package_data=True,
   zip_safe=False,
)
