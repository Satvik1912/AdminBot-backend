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
from app.services.excel_service import generate_excel
from fastapi.responses import FileResponse
from app.services.excel_service import get_excel_path
import uuid
import os


router = APIRouter()


@router.post("/generate-sql/")
async def process_user_input(
    request: UserInputRequest, 
    admin: dict = Depends(get_current_admin)  # Authentication enforced
):
    if not admin:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sql_query = generate_sql(request.user_input)

    if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
        return {"message": sql_query}
    elif sql_query.lower().startswith("select"):
        query_results = execute_sql_query(sql_query)
        formatted_response = format_results(query_results)

        # Generate a unique response ID
        response_id = str(uuid.uuid4())

        # Generate Excel asynchronously
        await generate_excel(response_id, query_results)

        return {
            "sql_query": sql_query,
            "results": query_results,
            "formatted": formatted_response,
            "response_id": response_id,  # Return response ID for later download
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid query generated.")

@router.get("/download-excel/{response_id}/")
async def download_excel(response_id: str, admin: dict = Depends(get_current_admin)):
    """Endpoint to download previously generated Excel files using response ID."""
    file_path = get_excel_path(response_id)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"export_{response_id}.xlsx")

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
