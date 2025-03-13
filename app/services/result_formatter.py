import google.generativeai as genai
from app.core.config import config
import json

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def format_results(results):
    """Formats SQL results into readable text using Gemini."""
    prompt = f"Format the following database query results into a readable sentence with insights:\n\n{json.dumps(results, indent=2)}"
    response = model.generate_content(prompt)
    return response.text.strip()
