import os
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from IPython.display import Image, display
from langgraph.checkpoint.memory import MemorySaver
import json
import sys 
sys.path.append(".") 
from my_state import MyState


load_dotenv()

memory = MemorySaver()
graph_builder = StateGraph(MyState)


def chatbot(state: MyState):
    return {
        "messages": [
            ChatGroq(temperature=0, model="openai/gpt-oss-20b").invoke(
                state["messages"]
            )
        ]
    }


graph_builder.add_node("chatbot", chatbot)

graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=memory)


def run_graph(user_input: str, thread_id: int):
    event = graph.invoke({"messages": [user_input]}, config={"configurable": {"thread_id": thread_id}})
    print(json.dumps(event, indent=2, default=str))



