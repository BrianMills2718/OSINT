# config.py - CONSTANTS ONLY, NO IMPORTS OF BUSINESS LOGIC
import os

# --- API Configuration ---
RAPIDAPI_TWITTER_HOST = "twitter-api45.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_TWITTER_HOST}"

# --- LLM Configuration ---
LLM_MODEL_NAME = "gpt-5-mini"  # Updated to latest GPT-5-mini model

# --- Application Settings ---
ENDPOINTS_FILE = "merged_endpoints.json"
ONTOLOGY_FILE = "ontology_synonyms.py"
DEFAULT_MAX_PAGES_FALLBACK = 3
API_TIMEOUT_SECONDS = 30  # Increased from 7s - logs show requests take 10-13s regularly

# REMOVED: All prompt loading functions and business logic imports
# Prompts are now handled by prompt_manager.py