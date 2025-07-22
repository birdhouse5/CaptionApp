"""
Setup script for Caption Tool.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="caption-tool",
    version="1.0.0",
    author="Caption Tool Team",
    description="AI-powered video captioning tool using OpenAI Whisper",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "caption-tool=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="video captions subtitles whisper ai transcription",
    project_urls={
        "Source": "https://github.com/username/caption-tool",
        "Bug Reports": "https://github.com/username/caption-tool/issues",
    },
    include_package_data=True,
    package_data={
        "": ["default_config.json"],
    },
)