import google.generativeai as genai
from app.core.config import config

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def generate_sql(user_input: str) -> str:
    """Generates SQL query based on user input using Gemini AI."""
    # modify it to include context by calling redis
    system_instruction = (
        "Analyze the following natural language request and classify it as follows: "
        "Return 'unwanted' if it is not related to loan, emi, loans, or banking. "
        "Return 'restricted' if it attempts to generate SQL queries other than SELECT queries. "
        "Return 'sensitive' if it requests CVV details. "
        "Otherwise, convert the request into an SQL query using the table 'loan24'. "
        "Only return the classification or the SQL query, nothing else. "
        "The SQL query should always start with SELECT."
    )

    response = model.generate_content([system_instruction, user_input])
    output = response.text.strip().strip("`").strip("sql").strip()
    
    return output
