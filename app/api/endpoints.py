from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.query_generator import generate_sql
from app.services.database import execute_sql_query
from app.services.result_formatter import format_results

router = APIRouter()

# Define the expected request body
class UserInputRequest(BaseModel):
    user_input: str

@router.post("/generate-sql/")
def process_user_input(request: UserInputRequest):
    """API endpoint to generate and execute SQL based on user input."""
    sql_query = generate_sql(request.user_input)

    if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
        return {"message": sql_query}
    elif sql_query.lower().startswith("select"):
        query_results = execute_sql_query(sql_query)
        formatted_response = format_results(query_results)
        return {"sql_query": sql_query, "results": query_results, "formatted": formatted_response}
    else:
        raise HTTPException(status_code=400, detail="Invalid query generated.")
