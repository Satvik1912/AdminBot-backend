from fastapi import APIRouter, HTTPException
from app.services.query_generator import generate_sql
from app.services.database import execute_sql_query
from app.services.result_formatter import format_results
from app.models.models import *
from fastapi import APIRouter, HTTPException, Depends
from app.models.admin import AdminSignup, AdminLogin, TokenResponse
from app.services.auth_services import admin_signup, admin_login
from app.core.security import get_current_admin
from app.services.visualization_service import get_chart_suggestion, generate_plotly_chart
from app.services.redis_service import *
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/generate-response/")
async def process_user_input(
    request: UserInputRequest, 
    admin: dict = Depends(get_current_admin)
):  
    """Generates SQL query, executes it, and returns results (Admin only)."""
    admin_id = admin["admin_id"]
    # sql_query = generate_sql(request.user_input)
    sql_query = "SELECT * FROM loan;"
    if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
        return {"message": sql_query}
    elif sql_query.lower().startswith("select"):
        # query_results = execute_sql_query(sql_query)
        query_results = [
            ("Approved", 150),
            ("Pending", 50),
            ("Rejected", 30)
        ]
        # formatted_response = format_results(query_results)
        formatted_response = "The chart describes what you have asked."
        chart_type = get_chart_suggestion(query_results, request.user_input)
        chart_img = generate_plotly_chart(query_results, chart_type, request.user_input)

        # Create a conversation record
        conversation_record = ConversationRecord(
            conversation_id=str(uuid.uuid4()),  # Generate UUID
            query=request.user_input,
            response=formatted_response,  # Convert response to string
            visualization=chart_img,
            timestamp=datetime.utcnow().isoformat(),
            data_type=[chart_type] if chart_type else []
        )

        if hasattr(request, "thread_id") and request.thread_id:
            # Append to an existing thread
            append_result = append_conversation(request.thread_id, conversation_record.dict())
            return {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": chart_type,
                "chart_image_url": chart_img,
                "message": "Conversation appended",
                "thread_id": request.thread_id,
                "conversation_count": append_result["total_conversations"]
            }
        else:
            # Create a new thread
            thread_id = str(uuid.uuid4())  # Generate a new thread ID
            thread_data = ThreadInsertRequest(
                thread_id=thread_id,
                admin_id=admin_id,
                chat_name=request.user_input,  # Use user_input as chat name
                conversations=[conversation_record]
            )
            insert_into_redis(thread_data.dict())
            return {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": chart_type,
                "chart_image_url": chart_img,
                "message": "New chat thread created",
                "thread_id": thread_id
            }
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
