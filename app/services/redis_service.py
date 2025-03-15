import redis
import json
import app.services.mongo_service as mongo
import logging
from app.core.config import config

# Initialize Redis client using values from config
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True
)

def insert_into_redis(data):
    thread_id = data["thread_id"]
    thread_key = f"admin_thread:{thread_id}"

    # Store thread details in a hash
    thread_data = {
        "thread_id": data["thread_id"],
        "admin_id": data["admin_id"],
        "chat_name": data["chat_name"],
    }
    redis_client.hset(thread_key, mapping=thread_data)

    # Store conversations in a list
    for conversation in data.get("conversations", []):
        redis_client.rpush(f"{thread_key}:conversations", json.dumps(conversation))

    return {"message": "Chat thread inserted successfully", "thread_id": thread_id}

def append_conversation(thread_id: str, conversation: dict):
    key = f"admin_thread:{thread_id}:conversations"

    # Convert dictionary to JSON string before storing in Redis
    conversation_json = json.dumps(conversation)

    # Append the conversation to the Redis list
    redis_client.rpush(key, conversation_json)

    # Get updated conversation count
    conversation_count = redis_client.llen(key)

    return {
        "status": "success",
        "message": f"Conversation appended successfully to thread {thread_id}.",
        "total_conversations": conversation_count
    }

# Function to get a record from Redis based on thread_id
def get_from_redis(thread_id):
    thread_key = f"admin_thread:{thread_id}"

    # Check if the key exists
    if not redis_client.exists(thread_key):
        return {"message": "Thread not found"}, 404

    thread_details = redis_client.hgetall(f"admin_thread:{thread_id}")
    conversations = redis_client.lrange(f"admin_thread:{thread_id}:conversations", 0, -1)

    thread_data = {
        "thread_details": thread_details,
        "conversations": [json.loads(conv) for conv in conversations]
    }
    return thread_data

# Function to delete a record from Redis
def delete_from_redis(thread_id):
    
    # Check if thread exists
    if not redis_client.exists(f"admin_thread:{thread_id}"):
        return {"message": "Thread not found"}, 404
    logging.info(mongo.migrate_thread_to_mongo(thread_id))
    # Delete thread and conversations
    redis_client.delete(f"admin_thread:{thread_id}")
    redis_client.delete(f"admin_thread:{thread_id}:conversations")

    return {"message": "Thread deleted", "thread_id": thread_id}
# Function to store Excel file path in Redis
def store_excel_path(conversation_id: str, file_path: str):
    """Store the Excel file path in Redis."""
    redis_client.set(f"excel:{conversation_id}", file_path)

# Function to retrieve the Excel file path from Redis
def get_excel_path(conversation_id: str):
    """Retrieve the Excel file path from Redis."""
    return redis_client.get(f"excel:{conversation_id}")

def get_last_n_conversations(thread_id: str, n: int = 5):
    """Fetch last N user queries from Redis for a given thread."""
    key = f"admin_thread:{thread_id}:conversations"

    # Get last `n` conversations from Redis
    conversations = redis_client.lrange(key, -n, -1)

    # Extract only user questions (queries) from conversations
    return [json.loads(conv)["query"] for conv in conversations if "query" in json.loads(conv)]
