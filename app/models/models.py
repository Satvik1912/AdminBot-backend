from pydantic import BaseModel
from typing import List, Optional

# Define the expected request body
class UserInputRequest(BaseModel):
    user_input: str
    
class ConversationRecord(BaseModel):
    conversation_id: str
    query: str
    response: str
    visualization: Optional[str] = None
    timestamp: str
    data_type: List[str]

class ThreadInsertRequest(BaseModel):
    thread_id: str
    admin_id: str
    chat_name: str
    conversations: List[ConversationRecord] = []
