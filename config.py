# config.py – Model names and project-level constants
import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter / Gemini model configuration  (đọc từ .env, fallback về default)
QUESTION_MODEL        = os.getenv("QUESTION_MODEL",        "google/gemini-2.5-flash-lite")
ANSWER_MODEL          = os.getenv("ANSWER_MODEL",          "google/gemini-2.5-flash-lite")
ANSWER_FALLBACK_MODEL = os.getenv("ANSWER_FALLBACK_MODEL", "google/gemini-2.5-flash-lite")
