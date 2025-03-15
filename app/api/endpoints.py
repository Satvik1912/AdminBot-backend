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
import os
from fastapi.responses import FileResponse
from app.services.excel_service import generate_excel
from app.services.redis_service import get_excel_path

router = APIRouter()
@router.post("/generate-response/")
async def process_user_input(
    request: UserInputRequest, 
    admin: dict = Depends(get_current_admin)
):  
    admin_id = admin["admin_id"]
    sql_query = generate_sql(request.user_input, request.thread_id if hasattr(request, "thread_id") else None)

    logging.info(sql_query)
    if sql_query.lower() in ["unwanted", "restricted", "sensitive"]:
        return {"message": sql_query}
    
    elif sql_query.lower().startswith("select"):
        query_results = execute_sql_query(sql_query)
        logging.info(f"Query Results Type: {type(query_results)}")
        formatted_response = format_results(query_results)
        chart_type = get_chart_suggestion(query_results, request.user_input)
        chart_img = generate_plotly_chart(query_results, chart_type, request.user_input)

        conversation_id = str(uuid.uuid4())  # Generate UUID

        conversation_record = ConversationRecord(
            conversation_id=conversation_id,
            query=request.user_input,
            response=formatted_response,
            visualization=chart_img,
            timestamp=datetime.utcnow().isoformat(),
            data_type=[chart_type] if chart_type else []
        )

        if hasattr(request, "thread_id") and request.thread_id:
            append_result = append_conversation(request.thread_id, conversation_record.dict())
            response_data = {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": chart_type,
                "chart_image_url": chart_img,
                "message": "Conversation appended",
                "thread_id": request.thread_id,
                "conversation_count": append_result["total_conversations"],
                "conversation_id": conversation_id
            }
        else:
            thread_id = str(uuid.uuid4())
            thread_data = ThreadInsertRequest(
                thread_id=thread_id,
                admin_id=admin_id,
                chat_name=request.user_input,
                conversations=[conversation_record]
            )
            insert_into_redis(thread_data.dict())
            response_data = {
                "sql_query": sql_query,
                "results": formatted_response,
                "chart_type": chart_type,
                "chart_image_url": chart_img,
                "message": "New chat thread created",
                "thread_id": thread_id,
                "conversation_id": conversation_id
            }

        # ✅ Generate Excel asynchronously
        await generate_excel(conversation_id, query_results)

        return response_data

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


@router.get("/download-excel/{conversation_id}/")
async def download_excel(conversation_id: str, admin: dict = Depends(get_current_admin)):
    """Endpoint to download an Excel file based on conversation ID."""
    file_path = get_excel_path(conversation_id)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"conversation_{conversation_id}.xlsx"
    )

@router.delete("/migrate-thread/{thread_id}")
async def migrate_and_delete_thread(thread_id: str):
    """
    Migrate a thread to MongoDB and delete it from Redis.
    """
    try:
        result = delete_from_redis(thread_id)
        
        if isinstance(result, tuple):  # Check if it returned an error
            raise HTTPException(status_code=result[1], detail=result[0]["message"])

        return {"message": "Thread successfully migrated and deleted from Redis."}

    except Exception as e:
        logging.error(f"Error migrating thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")