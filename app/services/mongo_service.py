from pymongo import MongoClient
from app.core.config import config  
from datetime import datetime

# Initialize MongoDB connection
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client[config.MONGO_DB_NAME]

threads_collection = db["threads"]
conversations_collection = db["conversations"]

def get_conversations_by_thread(admin_id: str, thread_id: str, page: int = 1, limit: int = 10):
    """
    Retrieve paginated conversations for a given thread_id and admin_id, sorted from latest to earliest.
    """
    query_filter = {"admin_id": admin_id, "thread_id": thread_id}  # Ensure correct filtering

    # Calculate how many documents to skip based on page number
    skip_count = (page - 1) * limit  

    # Fetch paginated conversations sorted by timestamp (latest first)
    conversations = list(
        conversations_collection.find(
            query_filter, 
            {"_id": 0, "thread_id": 0, "admin_id": 0, "data_type": 0}
        )
        .sort("timestamp", -1)  # Sort by latest first
        .skip(skip_count)       # Skip past pages
        .limit(limit)           # Limit per page
    )

    # Get total count for pagination metadata
    total_count = conversations_collection.count_documents(query_filter)
    total_pages = (total_count + limit - 1) // limit  # Calculate total pages

    return {
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_conversations": total_count,
        "conversations": conversations
    }


def get_threads_by_admin(admin_id: str, page: int = 1, limit: int = 10):
    """
    Retrieve paginated thread IDs and chat names for a given admin.
    """
    skip = (page - 1) * limit  # Calculate offset for pagination

    total_threads = threads_collection.count_documents({"admin_id": admin_id})  # Total count

    threads_cursor = threads_collection.find(
        {"admin_id": admin_id}, 
        {"thread_id": 1, "chat_name": 1, "_id": 0}
    ).skip(skip).limit(limit)

    threads = list(threads_cursor)  # Convert cursor to list

    return {
        "threads": threads,
        "page": page,
        "limit": limit,
        "total_threads": total_threads,
        "total_pages": (total_threads // limit) + (1 if total_threads % limit else 0)
    }

# ✅ Function to insert a new thread
def insert_into_threads(thread_id: str, admin_id: str, chat_name: str):
    thread_doc = {
        "thread_id": str(thread_id),
        "admin_id": admin_id,
        "chat_name": chat_name,
        "start_timestamp": datetime.utcnow().isoformat(),
        "end_timestamp": None  # Will be updated on new messages
    }
    threads_collection.insert_one(thread_doc)


# ✅ Function to insert a conversation and update the thread's end_timestamp
def insert_into_conversations(thread_id: str, admin_id: str, conversation: dict):
    conversation_doc = {
        "conversation_id": str(conversation["conversation_id"]),
        "thread_id": thread_id,
        "admin_id": admin_id,
        "query": conversation["query"],
        "response": conversation["response"],
        "visualization": conversation.get("visualization"),
        "timestamp": conversation["timestamp"],
        "data_type": conversation.get("data_type"),
        "cols": conversation.get("cols"),
        "rows": conversation.get("rows"),
        "excel_path": conversation["excel_path"]
    }
    conversations_collection.insert_one(conversation_doc)

    # ✅ Update thread's end_timestamp when a new conversation is added
    threads_collection.update_one(
        {"thread_id": thread_id},
        {"$set": {"end_timestamp": conversation["timestamp"]}}
    )
