from app.core.config import settings
from app.services.llm.openai_adapter import OpenAIModel
from app.services.llm.gemini_adapter import GeminiModel
from app.services.llm.claude_adapter import ClaudeModel


def get_llm_adapter(model_name: str):
    """Factory method to return the correct LLM adapter strategy."""
    model_name_clean = model_name.strip().lower()

    if model_name_clean == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured.")
        return OpenAIModel(api_key=settings.OPENAI_API_KEY)

    elif model_name_clean == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured.")
        return ClaudeModel(api_key=settings.ANTHROPIC_API_KEY)

    elif model_name_clean == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        return GeminiModel(api_key=settings.GEMINI_API_KEY)

    else:
        raise ValueError(
            f"Unsupported model: {model_name}. Please choose 'openai', 'claude', or 'gemini'.")
