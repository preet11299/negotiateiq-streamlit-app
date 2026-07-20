# utils/api_handler.py
import time

from google import genai

TIMEOUT_SECONDS = 30
RETRY_DELAY = 15

# ── Model registry (Google Gemini) ───────────────────────────────────────────
MODEL_OPTIONS = {
    "gemini-3.5-flash": "Gemini 3.5 Flash",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
}
DEFAULT_MODEL = "gemini-3.5-flash"


def call_llm(prompt: str, api_key: str, model_name: str = None,
             json_mode: bool = False) -> str:
    """
    Call the Gemini API. When json_mode is True, the model is constrained
    to return a valid JSON document (response_mime_type=application/json).
    """
    model_name = model_name or DEFAULT_MODEL
    try:
        client = genai.Client(
            api_key=api_key,
            http_options={"timeout": TIMEOUT_SECONDS * 1000},
        )
        config = {"response_mime_type": "application/json"} if json_mode else None
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
        if not response.text:
            raise APIError("Empty response from Gemini API")
        return response.text
    except (RateLimitError, AuthError, APIError, TimeoutError):
        raise
    except Exception as e:
        error_str = str(e)
        if "429" in error_str:
            raise RateLimitError("Rate limit reached")
        if "401" in error_str or "403" in error_str:
            raise AuthError("Invalid API key or access denied")
        if "timeout" in error_str.lower():
            raise TimeoutError(f"Request timed out after {TIMEOUT_SECONDS} seconds")
        raise APIError(f"API Error: {error_str}")


def call_llm_with_retry(prompt: str, api_key: str, retry_placeholder=None,
                        model_name: str = None, json_mode: bool = False) -> str:
    """
    Wraps call_llm with one automatic retry on rate limit.
    Shows countdown in UI if retry_placeholder is provided (st.empty()).
    """
    try:
        return call_llm(prompt, api_key, model_name, json_mode)
    except RateLimitError:
        if retry_placeholder:
            for i in range(RETRY_DELAY, 0, -1):
                filled = int((RETRY_DELAY - i) / RETRY_DELAY * 10)
                bar = "█" * filled + "░" * (10 - filled)
                retry_placeholder.warning(
                    f"⚠️ Rate limit reached\n\nAutomatically retrying in {i} seconds...\n\n[{bar}] {i}s remaining"
                )
                time.sleep(1)
            retry_placeholder.empty()
        else:
            time.sleep(RETRY_DELAY)
        return call_llm(prompt, api_key, model_name, json_mode)


def estimate_token_cost(num_suppliers: int, model_name: str = None) -> dict:
    """Rough token cost estimate for sidebar display."""
    model_name = model_name or DEFAULT_MODEL
    total_tokens = num_suppliers * 1250
    model_label = MODEL_OPTIONS.get(model_name, model_name)
    return {
        "total_tokens": total_tokens,
        "cost_str": f"Free ({model_label})",
        "suppliers": num_suppliers,
    }


# ── Custom exceptions ─────────────────────────────────────────────────────────
class RateLimitError(Exception):
    pass

class AuthError(Exception):
    pass

class APIError(Exception):
    pass

class TimeoutError(Exception):
    pass
