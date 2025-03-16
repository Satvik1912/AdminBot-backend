# import google.generativeai as genai
# from app.core.config import config
# import json

# # Configure Gemini API
# genai.configure(api_key=config.GEMINI_API_KEY)
# model = genai.GenerativeModel("gemini-2.0-flash")

# def format_results(results):
#     """Formats SQL results into readable text using Gemini."""
#     prompt = f"Format the following database query results into a readable sentence with insights:\n\n{json.dumps(results, indent=2)}"
#     response = model.generate_content(prompt)
#     return response.text.strip()

import json
import google.generativeai as genai
from app.core.config import config
import datetime

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def serialize_dates(obj):
    """Helper function to convert datetime objects to strings"""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def format_results(results):
    """Formats SQL results into readable text using Gemini."""
    try:
        formatted_data = json.dumps(results, indent=2, default=serialize_dates)  # Convert dates to strings
        prompt = f"Format the following database query results into a readable sentence with insights:\n\n{formatted_data}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error formatting results: {str(e)}"
