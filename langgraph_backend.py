from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from mongo_handler import MongoChatDB  # Ye import sahi hai?

# ---------------- LOAD ENV ----------------
load_dotenv()

# ---------------- STATE ----------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ---------------- LLM ----------------
llm = ChatGroq(
    model="llama-3.1-8b-instant"
)

# ---------------- NODE ----------------
def chat_node(state: ChatState):
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

# ---------------- MEMORY ----------------
checkpointer = MemorySaver()

# ---------------- GRAPH ----------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

# 🔴 YAHAN PE GALTI THI - Initialize MongoDB properly
# MongoDB initialize karo - YEH LINE IMPORTANT HAI
print("🔄 Initializing MongoDB...")
mongo_db = MongoChatDB()  # <-- YEH LINE MISSING THI
print("✅ MongoDB initialized!")

# ---------------- NORMAL RESPONSE ----------------
def get_ai_response(user_text: str, thread_id: str = "default"):
    result = chatbot.invoke(
        {"messages": [HumanMessage(content=user_text)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content

# ---------------- STREAMING RESPONSE ----------------
def stream_ai_response(user_text: str, thread_id: str):
    """
    Streaming WITH memory using LangGraph
    """
    events = chatbot.stream(
        {"messages": [HumanMessage(content=user_text)]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="messages",
    )

    for event in events:
        if event[0].content:
            yield event[0].content

# ---------------- MONGODB FUNCTIONS ----------------
def load_chat_history(thread_id: str):
    """Load chat history from MongoDB"""
    return mongo_db.get_conversation(thread_id)

def save_chat_message(thread_id: str, role: str, content: str, user_id: str = "default_user"):
    """Save chat message to MongoDB"""
    return mongo_db.save_message(thread_id, role, content, user_id)

def get_user_chats(user_id: str = "default_user"):
    """Get all chats for a user"""
    return mongo_db.get_user_conversations(user_id)