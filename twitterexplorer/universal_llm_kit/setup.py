"""
Setup script for Universal LLM Kit
Run: pip install -e . to install as editable package
"""

from setuptools import setup, find_packages

setup(
    name="universal-llm-kit",
    version="1.0.0",
    description="Universal interface for all major LLM providers with automatic optimization",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "litellm>=1.0.0",
        "python-dotenv>=1.0.0", 
        "pydantic>=2.0.0",
        "instructor>=1.0.0",
        "aiohttp>=3.8.0"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)