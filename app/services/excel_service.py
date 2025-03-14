import pandas as pd
import uuid
import os
from datetime import datetime
from app.core.config import EXCEL_STORAGE_PATH

# Ensure the storage directory exists
os.makedirs(EXCEL_STORAGE_PATH, exist_ok=True)

# Dictionary to store response IDs mapping to file paths
response_store = {}

async def generate_excel(response_id: str, data: list):
    """
    Asynchronously generate an Excel file from query results.
    """
    df = pd.DataFrame(data)  # Convert query results to DataFrame
    file_path = os.path.join(EXCEL_STORAGE_PATH, f"{response_id}.xlsx")
    
    df.to_excel(file_path, index=False)  # Save to Excel
    response_store[response_id] = file_path  # Store response ID mapping
    
    return file_path

def get_excel_path(response_id: str):
    """Retrieve the file path for a given response ID."""
    return response_store.get(response_id)
