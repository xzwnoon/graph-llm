import os

# Neo4j Database Configuration
# Replace with your actual Neo4j connection details
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "GHr17wA66RyrS-VICFGCifLQVswtUydL0PCXKTx25Z4")

# OpenRouter / DeepSeek LLM API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-0bb6e4dae7ed44b58a8585b363c95dfb")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 8192))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.5))
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 120))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", 8))
