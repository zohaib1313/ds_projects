import streamlit as st
import asyncio
import json
import datetime
from typing import Dict, Any, List
from dataclasses import dataclass
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import pandas as pd
import threading
import time
import schedule
from PIL import Image
import base64
from io import BytesIO

# Load environment variables
load_dotenv()

@dataclass
class ScheduledTask:
    id: str
    task: str
    scheduled_time: datetime.datetime
    status: str = "pending"
    created_at: datetime.datetime = datetime.datetime.now()
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.now()

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        
    def add_task(self, task: ScheduledTask):
        self.tasks.append(task)
        
    def get_pending_tasks(self):
        return [t for t in self.tasks if t.status == "pending"]
    
    def get_all_tasks(self):
        return self.tasks
    
    def execute_task(self, task: ScheduledTask, agent):
        try:
            # Execute the task using the agent
            result = asyncio.run(agent.ainvoke({
                "messages": [{"role": "user", "content": task.task}]
            }))
            
            # Extract response using helper function
            response = extract_message_content(result)
            task.status = "completed"
            return response
            
        except Exception as e:
            task.status = f"failed: {str(e)}"
            return None

def extract_message_content(result):
    """Helper to extract message content from agent result"""
    if hasattr(result, 'messages') and result.messages:
        return result.messages[-1].content
    elif isinstance(result, dict) and 'messages' in result:
        return result['messages'][-1]['content']
    else:
        return str(result)

def parse_schedule_command(message: str) -> Dict[str, Any]:
    """Parse scheduling commands from user messages"""
    import re
    
    # Pattern to match scheduling commands
    patterns = [
        r"send message to (\w+) at (\d{1,2}):(\d{2})\s*(am|pm)?\s*(.+)?",
        r"remind me at (\d{1,2}):(\d{2})\s*(am|pm)?\s*to\s*(.+)",
        r"schedule (.+) for (\d{1,2}):(\d{2})\s*(am|pm)?",
        r"at (\d{1,2}):(\d{2})\s*(am|pm)?\s*(.+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            groups = match.groups()
            
            if "send message to" in message.lower():
                recipient = groups[0]
                hour = int(groups[1])
                minute = int(groups[2])
                period = groups[3] if groups[3] else None
                task_content = groups[4] if len(groups) > 4 and groups[4] else message
                
                # Adjust for AM/PM
                if period == "pm" and hour != 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0
                
                scheduled_time = datetime.datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                if scheduled_time <= datetime.datetime.now():
                    scheduled_time += datetime.timedelta(days=1)
                
                return {
                    "is_scheduled": True,
                    "task": f"send message to {recipient}: {task_content}",
                    "scheduled_time": scheduled_time,
                    "type": "message"
                }
    
    return {"is_scheduled": False}

def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def init_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "mcp_client" not in st.session_state:
        st.session_state.mcp_client = None
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = TaskScheduler()
    if "tools_loaded" not in st.session_state:
        st.session_state.tools_loaded = False

async def setup_agent():
    """Setup the LangGraph agent with MCP tools"""
    try:
        # Connect to MCP server
        client = MultiServerMCPClient({
            "whatsapp": {
                "command": "python",
                "args": ["main.py"],
                "transport": "stdio"
            }
        })
        
        # Load tools
        tools = await client.get_tools()
        
        # Initialize LLM
        llm = ChatGroq(temperature=0, model="openai/gpt-oss-20b")
        
        # Create agent
        agent = create_react_agent(llm, tools)
        
        return agent, client, tools
    except Exception as e:
        st.error(f"Failed to setup agent: {str(e)}")
        return None, None, []

def main():
    st.set_page_config(
        page_title="LangGraph Chat Assistant", 
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Sidebar for configuration
    with st.sidebar:
        st.title("🤖 Chat Assistant")
        
        # Agent Setup
        st.header("Agent Setup")
        if st.button("Initialize Agent"):
            with st.spinner("Setting up agent..."):
                try:
                    agent, client, tools = asyncio.run(setup_agent())
                    if agent:
                        st.session_state.agent = agent
                        st.session_state.mcp_client = client
                        st.session_state.tools_loaded = True
                        st.success(f"Agent initialized with {len(tools)} tools!")
                        st.json([tool.name for tool in tools])
                    else:
                        st.error("Failed to initialize agent")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Model Selection
        st.header("Model Configuration")
        model_type = st.selectbox(
            "Select Model Provider",
            ["Groq", "OpenAI"]
        )
        
        if model_type == "Groq":
            model_name = st.selectbox(
                "Groq Model",
                ["openai/gpt-oss-20b", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            )
        else:
            model_name = st.selectbox(
                "OpenAI Model", 
                ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
            )
        
        temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
        
        # Scheduled Tasks
        st.header("📅 Scheduled Tasks")
        
        # Display pending tasks
        pending_tasks = st.session_state.scheduler.get_pending_tasks()
        if pending_tasks:
            st.subheader("Pending Tasks")
            for task in pending_tasks:
                with st.expander(f"Task: {task.id}"):
                    st.write(f"**Task:** {task.task}")
                    st.write(f"**Scheduled:** {task.scheduled_time.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Status:** {task.status}")
        
        # All tasks history
        all_tasks = st.session_state.scheduler.get_all_tasks()
        if st.button("View All Tasks"):
            if all_tasks:
                df = pd.DataFrame([
                    {
                        "ID": task.id,
                        "Task": task.task[:50] + "..." if len(task.task) > 50 else task.task,
                        "Scheduled": task.scheduled_time.strftime('%H:%M'),
                        "Status": task.status,
                        "Created": task.created_at.strftime('%Y-%m-%d %H:%M')
                    } for task in all_tasks
                ])
                st.dataframe(df)
            else:
                st.info("No tasks scheduled yet")
    
    # Main chat interface
    st.title("💬 LangGraph Chat Assistant")
    
    if not st.session_state.tools_loaded:
        st.warning("⚠️ Please initialize the agent first using the sidebar!")
        return
    
    # Chat interface
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message.get("type") == "image":
                    st.image(message["content"], caption="Uploaded Image", use_column_width=True)
                elif message.get("type") == "file":
                    st.write(f"📎 File: {message['filename']}")
                    if st.download_button(
                        label="Download",
                        data=message["content"],
                        file_name=message["filename"],
                        mime=message.get("mime", "application/octet-stream")
                    ):
                        st.success("File ready for download!")
                else:
                    st.markdown(message["content"])
    
    # File upload area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Text input
        user_input = st.chat_input("Type your message here...")
    
    with col2:
        # Media upload
        uploaded_file = st.file_uploader(
            "Upload media",
            type=['png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx'],
            label_visibility="collapsed"
        )
    
    # Handle file upload
    if uploaded_file is not None:
        file_details = {
            "filename": uploaded_file.name,
            "filetype": uploaded_file.type,
            "filesize": uploaded_file.size
        }
        
        # Handle different file types
        if uploaded_file.type.startswith('image/'):
            image = Image.open(uploaded_file)
            st.session_state.messages.append({
                "role": "user",
                "content": image,
                "type": "image",
                "filename": uploaded_file.name
            })
            
            # Convert image for processing
            img_b64 = image_to_base64(image)
            user_input = f"I've uploaded an image: {uploaded_file.name}. Please analyze it."
            
        else:
            # Handle other file types
            file_content = uploaded_file.read()
            st.session_state.messages.append({
                "role": "user", 
                "content": file_content,
                "type": "file",
                "filename": uploaded_file.name,
                "mime": uploaded_file.type
            })
            user_input = f"I've uploaded a file: {uploaded_file.name}. Please process it."
    
    # Handle user input
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Check if it's a scheduling command
        schedule_info = parse_schedule_command(user_input)
        
        if schedule_info["is_scheduled"]:
            # Create scheduled task
            task_id = f"task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            scheduled_task = ScheduledTask(
                id=task_id,
                task=schedule_info["task"],
                scheduled_time=schedule_info["scheduled_time"]
            )
            
            st.session_state.scheduler.add_task(scheduled_task)
            
            response = f"✅ Task scheduled successfully!\n\n**Task:** {schedule_info['task']}\n**Scheduled for:** {schedule_info['scheduled_time'].strftime('%Y-%m-%d %H:%M')}\n**Task ID:** {task_id}"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        else:
            # Process with agent
            with st.spinner("Processing..."):
                try:
                    result = asyncio.run(st.session_state.agent.ainvoke({
                        "messages": [{"role": "user", "content": user_input}]
                    }))
                    print(result)
                    response = result['messages'][-1].content
                    
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    
                    error_msg = f"❌ Error processing request: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # Refresh the page to show new messages
        st.rerun()

# Task execution scheduler (runs in background)
def run_scheduler():
    """Background task scheduler"""
    while True:
        try:
            if hasattr(st.session_state, 'scheduler'):
                pending_tasks = st.session_state.scheduler.get_pending_tasks()
                current_time = datetime.datetime.now()
                
                for task in pending_tasks:
                    if current_time >= task.scheduled_time:
                        if hasattr(st.session_state, 'agent') and st.session_state.agent:
                            st.session_state.scheduler.execute_task(task, st.session_state.agent)
            
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(60)

# Start background scheduler
if __name__ == "__main__":
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    main()