from .logger import log


def generate_content(api_key: str, prompt: str, primary_model: str = "gemini-2.5-pro") -> str:
    """
    Calls Gemini API with automatic model fallback on 503/UNAVAILABLE errors.
    Tries primary_model first, then falls back through cheaper/faster alternatives.
    """
    fallbacks = {
        "gemini-2.5-pro": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "gemini-1.5-flash": ["gemini-2.0-flash", "gemini-1.5-pro"],
    }
    models_to_try = [primary_model] + fallbacks.get(primary_model, ["gemini-2.0-flash", "gemini-1.5-pro"])
    last_error = None

    for model_name in models_to_try:
        try:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model=model_name, contents=prompt)
            except ImportError:
                import google.generativeai as genai_old
                genai_old.configure(api_key=api_key)
                response = genai_old.GenerativeModel(model_name).generate_content(prompt)

            if model_name != primary_model:
                log.info(f"Použit záložní Gemini model: {model_name} (primární {primary_model} nedostupný)")
            return response.text

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                log.warning(f"Gemini model {model_name} nedostupný (503), zkouším záložní...")
                last_error = e
                continue
            raise  # jiné chyby okamžitě dál

    raise last_error  # všechny modely selhaly
