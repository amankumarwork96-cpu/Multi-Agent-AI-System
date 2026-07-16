"""
Configuration
-------------
Loads environment variables and validates required secrets before any
agent tries to use them. Fails fast and clearly if something is missing,
rather than letting a cryptic error surface deep inside an LLM call.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing. Create a .env file in the project root "
        "with a line like: GROQ_API_KEY=your_key_here "
        "(see .env.example for the expected format)."
    )