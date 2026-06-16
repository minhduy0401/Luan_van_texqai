# config.py – Model names and project-level constants (runtime sync from DB)
DEFAULT_QUESTION_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_ANSWER_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_ANSWER_FALLBACK_MODEL = "google/gemini-2.5-flash-lite"

QUESTION_MODEL = DEFAULT_QUESTION_MODEL
ANSWER_MODEL = DEFAULT_ANSWER_MODEL
ANSWER_FALLBACK_MODEL = DEFAULT_ANSWER_FALLBACK_MODEL


def sync_from_db():
    """Load active AI model from system_settings into module-level constants."""
    from utils.app_settings import get_setting
    model = get_setting('ai_model', DEFAULT_QUESTION_MODEL).strip()
    if not model:
        model = DEFAULT_QUESTION_MODEL
    global QUESTION_MODEL, ANSWER_MODEL, ANSWER_FALLBACK_MODEL
    QUESTION_MODEL = ANSWER_MODEL = ANSWER_FALLBACK_MODEL = model
