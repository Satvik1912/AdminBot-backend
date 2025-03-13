from fastapi import FastAPI
from app.api.endpoints import router

app = FastAPI(title="Loan Chatbot API")

# Register API routes
app.include_router(router)
