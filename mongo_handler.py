from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class MongoChatDB:
    def __init__(self):
        try:
            # MongoDB Atlas connection
            mongo_uri = os.getenv("MONGODB_URI", "mongodb+srv://ramprasadlondhe24_db_user:ram123@cluster0.pauhzue.mongodb.net/")
            
            print(f"🔄 Connecting to MongoDB Atlas...")
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.admin.command('ping')
            print("✅ MongoDB connected successfully!")
            
            self.db = self.client["chatbot_db"]  # Database name
            self.conversations = self.db["conversations"]  # Collection name
            
            # Create indexes
            self.conversations.create_index("thread_id", unique=True, sparse=True)
            self.conversations.create_index("user_id")
            
            # Test collection by inserting a test document
            test_result = self.conversations.insert_one({
                "test": True,
                "timestamp": datetime.utcnow()
            })
            self.conversations.delete_one({"_id": test_result.inserted_id})
            print("✅ Collection is working!")
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            self.client = None
            self.db = None
            self.conversations = None
    
    def save_message(self, thread_id, role, content, user_id="default_user"):
        """Save message to MongoDB"""
        try:
            # ✅ FIX: Check if conversations exists (not using bool())
            if self.conversations is None:
                print("⚠️ MongoDB not available, message not saved")
                return False
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            }
            
            # Upsert - update if exists, insert if not
            result = self.conversations.update_one(
                {"thread_id": thread_id},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$setOnInsert": {
                        "user_id": user_id,
                        "created_at": datetime.utcnow(),
                        "thread_id": thread_id
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✅ New conversation created for thread: {thread_id[:8]}...")
            else:
                print(f"✅ Message added to thread: {thread_id[:8]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving message: {e}")
            return False
    
    def get_conversation(self, thread_id):
        """Get conversation from MongoDB"""
        try:
            # ✅ FIX: Check if conversations exists
            if self.conversations is None:
                return []
            
            conversation = self.conversations.find_one(
                {"thread_id": thread_id},
                {"_id": 0, "messages": 1}
            )
            
            if conversation and "messages" in conversation:
                messages = []
                for msg in conversation["messages"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                print(f"✅ Loaded {len(messages)} messages for thread: {thread_id[:8]}...")
                return messages
            
            print(f"📝 No messages found for thread: {thread_id[:8]}...")
            return []
            
        except Exception as e:
            print(f"❌ Error getting conversation: {e}")
            return []
    
    def get_user_conversations(self, user_id="default_user"):
        """Get all conversations for a user"""
        try:
            # ✅ FIX: Check if conversations exists
            if self.conversations is None:
                print("⚠️ MongoDB not available")
                return []
            
            # Get all conversations for user, sorted by updated_at
            conversations = list(self.conversations.find(
                {"user_id": user_id}
            ).sort("updated_at", -1).limit(50))
            
            print(f"📊 Found {len(conversations)} conversations for user {user_id[:8]}...")
            
            result = []
            for conv in conversations:
                # Get preview from first user message
                preview = "New conversation"
                if conv.get("messages") and len(conv["messages"]) > 0:
                    for msg in conv["messages"]:
                        if msg["role"] == "user":
                            preview = msg["content"][:30] + "..."
                            break
                
                result.append({
                    "thread_id": conv["thread_id"],
                    "preview": preview,
                    "updated_at": conv.get("updated_at", datetime.utcnow()),
                    "message_count": len(conv.get("messages", []))
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting user conversations: {e}")
            return []
    
    def delete_conversation(self, thread_id):
        """Delete a conversation"""
        try:
            if self.conversations is None:
                return False
            
            result = self.conversations.delete_one({"thread_id": thread_id})
            if result.deleted_count > 0:
                print(f"✅ Deleted conversation: {thread_id[:8]}...")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error deleting conversation: {e}")
            return False