import os

from google import genai

# Change this if Google retires/renames the model (see ai.google.dev/gemini-api/docs/models)
MODEL_NAME = "gemini-3.5-flash"

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

    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    return response.text or "The model returned an empty response. Please try again."
