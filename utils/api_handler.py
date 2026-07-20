# utils/api_handler.py
import time

TIMEOUT_SECONDS = 30
RETRY_DELAY = 15

PROVIDERS = ["Google Gemini", "Groq", "OpenAI", "Anthropic"]
DEFAULT_PROVIDER = "Google Gemini"

MODEL_REGISTRIES = {
    "Google Gemini": {
        "gemini-3.5-flash": "Gemini 3.5 Flash",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
        "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    },
    "Groq": {
        "llama-3.1-70b-versatile": "Llama 3.1 (70B)",
        "llama-3.1-8b-instant": "Llama 3.1 (8B)",
        "mixtral-8x7b-32768": "Mixtral (8x7B)",
    },
    "OpenAI": {
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-3.5-turbo": "GPT-3.5 Turbo",
    },
    "Anthropic": {
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
        "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
        "claude-3-opus-20240229": "Claude 3 Opus",
    }
}

def get_default_model(provider: str) -> str:
    return list(MODEL_REGISTRIES.get(provider, {}).keys())[0] if provider in MODEL_REGISTRIES else ""

def call_llm(prompt: str, api_key: str, provider: str = "Google Gemini", model_name: str = None, json_mode: bool = False) -> str:
    """
    Call the selected provider's LLM API. 
    When json_mode is True, the model is constrained to return valid JSON.
    """
    model_name = model_name or get_default_model(provider)
    
    try:
        if provider == "Google Gemini":
            from google import genai
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
            
        elif provider == "Groq":
            from groq import Groq
            client = Groq(api_key=api_key, timeout=TIMEOUT_SECONDS)
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            content = response.choices[0].message.content
            if not content:
                raise APIError("Empty response from Groq API")
            return content
            
        elif provider == "OpenAI":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS)
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            content = response.choices[0].message.content
            if not content:
                raise APIError("Empty response from OpenAI API")
            return content
            
        elif provider == "Anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key, timeout=TIMEOUT_SECONDS)
            
            if json_mode:
                prompt += "\n\nRespond ONLY with a valid JSON object. Do not include markdown formatting or introductory text."
                
            response = client.messages.create(
                model=model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
            if not content:
                raise APIError("Empty response from Anthropic API")
            return content
            
        else:
            raise APIError(f"Unsupported provider: {provider}")
            
    except (RateLimitError, AuthError, APIError, TimeoutError):
        raise
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate_limit" in error_str.lower():
            raise RateLimitError("Rate limit reached")
        if "401" in error_str or "403" in error_str or "authentication" in error_str.lower():
            raise AuthError("Invalid API key or access denied")
        if "timeout" in error_str.lower():
            raise TimeoutError(f"Request timed out after {TIMEOUT_SECONDS} seconds")
        raise APIError(f"API Error: {error_str}")


def call_llm_with_retry(prompt: str, api_key: str, retry_placeholder=None,
                        provider: str = "Google Gemini",
                        model_name: str = None, json_mode: bool = False) -> str:
    """
    Wraps call_llm with one automatic retry on rate limit.
    Shows countdown in UI if retry_placeholder is provided (st.empty()).
    """
    try:
        return call_llm(prompt, api_key, provider, model_name, json_mode)
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
        return call_llm(prompt, api_key, provider, model_name, json_mode)


def estimate_token_cost(num_suppliers: int, provider: str = "Google Gemini", model_name: str = None) -> dict:
    """Rough token cost estimate for sidebar display."""
    model_name = model_name or get_default_model(provider)
    total_tokens = num_suppliers * 1250
    model_label = MODEL_REGISTRIES.get(provider, {}).get(model_name, model_name)
    return {
        "total_tokens": total_tokens,
        "cost_str": f"Estimated ({model_label})",
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
