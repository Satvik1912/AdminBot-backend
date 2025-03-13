from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.query_generator import generate_sql
from app.services.database import execute_sql_query
from app.services.result_formatter import format_results
from app.models.models import UserInputRequest
from fastapi import APIRouter, HTTPException, Depends
from app.models.admin import AdminSignup, AdminLogin, TokenResponse
from app.services.auth_services import admin_signup, admin_login
from app.core.security import get_current_admin

router = APIRouter()

# ✅ Define Pydantic model for JSON input
class UserInputRequest(BaseModel):
    user_input: str

@router.post("/generate-sql/")
async def process_user_input(
    request: UserInputRequest, 
    admin: dict = Depends(get_current_admin)
):  
    """Generates SQL query, executes it, and returns results (Admin only)."""
    sql_query = generate_sql(request.user_input)

    if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
        return {"message": sql_query}
    elif sql_query.lower().startswith("select"):
        query_results = execute_sql_query(sql_query)
        return {"sql_query": sql_query, "results": query_results}
    else:
        raise HTTPException(status_code=400, detail="Invalid query generated.")

@router.post("/admin/signup/", response_model=dict)
async def signup(admin: AdminSignup):
    """Registers a new admin"""
    response = await admin_signup(admin)
    if "error" in response:
        raise HTTPException(status_code=400, detail=response["error"])
    return response

@router.post("/admin/login/", response_model=TokenResponse)
async def login(admin: AdminLogin):
    """Logs in an admin and returns JWT token"""
    token_data = await admin_login(admin.email, admin.password)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return token_data

@router.get("/admin/dashboard/")
async def dashboard(admin: dict = Depends(get_current_admin)):
    """Protected admin dashboard"""
    return {"message": f"Welcome, {admin['email']}!"}
