from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class MyState(TypedDict):
    messages: Annotated[list[str], add_messages]