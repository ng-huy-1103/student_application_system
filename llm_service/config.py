"""
Configuration for LLM service.
"""
import os

# Service configuration
LLM_SERVICE_HOST = os.getenv('LLM_SERVICE_HOST', '0.0.0.0')
LLM_SERVICE_PORT = int(os.getenv('LLM_SERVICE_PORT', 5002))

# Ollama configuration
OLLAMA_API_BASE = os.getenv('OLLAMA_API_BASE', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2:7b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', 120))

# Generation parameters
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 1024))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.3))
TOP_P = float(os.getenv('TOP_P', 0.9))
TOP_K = int(os.getenv('TOP_K', 50))

# System prompt
SYSTEM_PROMPT = """
You are an AI assistant specialized in analyzing student applications for a master's program at a Russian university.
Your task is to extract and summarize information from various documents, including passports, CVs, degree certificates, 
motivation letters, recommendation letters, language certificates, achievements, and additional documents.

Please provide all responses in English .
"""
