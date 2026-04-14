"""
Inference module for GlitchHunter.

Provides LLM inference capabilities using llama-cpp-python with OpenAI-compatible API.

Exports:
    - InferenceEngine: Main inference engine class
    - ModelLoader: Model loading and management
    - OpenAIAPI: OpenAI-compatible API wrapper
"""

from inference.engine import InferenceEngine
from inference.model_loader import ModelLoader
from inference.openai_api import OpenAIAPI

__all__ = [
    "InferenceEngine",
    "ModelLoader",
    "OpenAIAPI",
]
