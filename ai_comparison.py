import os
import time

from google import genai

# Tried in order. If one is overloaded or unavailable, the next one is used.
# Check ai.google.dev/gemini-api/docs/models if Google renames or retires a model.
MODEL_NAMES = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

# Temporary / model-side problems worth retrying: busy, rate limit, model not found
RETRYABLE_CODES = {404, 429, 500, 502, 503, 504}

_client = None


def _get_api_key():
    """Read the key from Streamlit secrets (deployment) or an env variable (local)."""
    try:
        import streamlit as st

        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets file locally - fall back to environment variable
    return os.getenv("GEMINI_API_KEY")


def _get_client():
    """Create the Gemini client only when it is first needed (not at import time)."""
    global _client
    if _client is None:
        api_key = _get_api_key()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to .streamlit/secrets.toml "
                "locally, or to the app's Secrets on Streamlit Community Cloud."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def compare_papers(summary1, summary2):
    prompt = f"""
You are an expert research assistant.

Compare the following two research papers.

PAPER 1:
{summary1 or "No summary available."}

PAPER 2:
{summary2 or "No summary available."}

Provide the comparison using these sections:

1. Research Objectives
2. Methodology
3. Key Findings
4. Similarities
5. Key Differences
6. Limitations
7. Research Gaps
8. Future Research Opportunities

Make the explanation clear and easy to understand.
Use bullet points where appropriate.
Base the comparison only on the information provided.
"""

    client = _get_client()
    last_error = None

    for model_name in MODEL_NAMES:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text or (
                    "The model returned an empty response. Please try again."
                )
            except Exception as error:
                code = getattr(error, "code", None)
                text = str(error)
                retryable = code in RETRYABLE_CODES or any(
                    word in text for word in ("UNAVAILABLE", "RESOURCE_EXHAUSTED")
                )
                if not retryable:
                    raise  # e.g. invalid API key - fail immediately
                last_error = error
                if attempt == 0:
                    time.sleep(2)  # short pause, then one retry on same model

    raise RuntimeError(
        "Gemini is busy right now. Please wait a minute and try again. "
        f"(Last error: {last_error})"
    )
