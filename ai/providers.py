import streamlit as st
import json

def get_chat_callable():
    """
    Returns: callable(prompt:str, system:str|None=None) -> str
    Providers supported:
      - gemini  (Google AI Studio free tier)
      - openai  (kept for fallback if you ever need it)
    Reads config from st.secrets["llm"].
    """
    cfg = (st.secrets.get("llm") or {})
    provider = str(cfg.get("provider", "gemini")).lower()

    # --- Google Gemini ---
    if provider == "gemini":
        try:
            import google.generativeai as genai
        except Exception:
            def _no_pkg(prompt, system=None):
                return ("Gemini SDK not installed. "
                        "Add 'google-generativeai' to requirements.txt and pip install.")
            return _no_pkg

        api_key = cfg.get("gemini_api_key")
        model_name = cfg.get("model", "gemini-1.5-flash")
        if not api_key:
            def _no_key(prompt, system=None):
                return "Gemini key missing. Add [llm].gemini_api_key to .streamlit/secrets.toml"
            return _no_key

        genai.configure(api_key=api_key)

        def _chat(prompt: str, system: str | None = None) -> str:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    system_instruction=system or ""
                )
                resp = model.generate_content(prompt)
                return resp.text or "(Empty response)"
            except Exception as e:
                return f"Gemini error: {e}"
        return _chat

    # --- OpenAI (optional fallback) ---
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=cfg["openai_api_key"])
            model = cfg.get("model", "gpt-4o-mini")
        except Exception:
            def _no_llm(prompt, system=None):
                return "OpenAI not configured. Set [llm].provider='gemini' for free tier."
            return _no_llm

        def _chat(prompt: str, system: str | None = None) -> str:
            msgs = []
            if system: msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            resp = client.chat.completions.create(
                model=model, messages=msgs, temperature=0.2
            )
            return resp.choices[0].message.content
        return _chat

    # Fallback
    def _unknown(prompt, system=None):
        return "Unknown provider. Set [llm].provider='gemini' in secrets.toml."
    return _unknown
