from langchain_openai import ChatOpenAI

from ai_gym_rat.core.config import settings 

def get_llm(temperature: float = 0.2):
    """
    Initializes and returns the LLM based on global AppSettings.
    """
    provider = settings.LLM_PROVIDER.lower()
    model_name = settings.LLM_MODEL_NAME

    if provider == "openai":
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment settings.")
        default_model = "gpt-4o-mini"
        return ChatOpenAI(
            model=model_name if model_name else default_model,
            temperature=temperature,
            api_key=api_key
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Check LLM_PROVIDER in settings.")