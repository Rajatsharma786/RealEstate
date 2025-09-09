"""
State definitions for the Real Estate Agent LangGraph.

This module defines the state structure and output models used throughout
the graph execution workflow.
"""

from typing import List, TypedDict, Annotated, Optional, Dict, Any
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class State(TypedDict):
    """
    Main state structure for the Real Estate Agent graph.
    
    This state is passed between nodes and contains all the information
    needed for the real estate analysis workflow.
    """
    # User input
    question: str
    
    # Context and retrieval
    context: List[str]
    
    # SQL generation and execution
    needs_sql: bool
    sql_result: str
    llm_sql: str
    
    # Conversation history
    messages: Annotated[list, add_messages]
    
    # Report generation
    report: str
    
    # Email functionality
    needs_email: bool
    email_state: Optional[Dict[str, Any]]
    user_id: str


class State_Output(BaseModel):
    """
    Structured output model for SQL query generation.
    
    This model ensures that the LLM returns properly formatted SQL queries
    that can be safely executed against the database.
    """
    sql_query: str = Field(
        ..., 
        description="The SQL query to execute against the properties database."
    )


class EmailState(BaseModel):
    """
    State information for email operations.
    
    Contains the result of email sending operations and any error information.
    """
    ok: bool = Field(description="Whether the email was sent successfully")
    message: str = Field(description="Status message or error description")
    recipient: Optional[str] = Field(
        default=None, 
        description="Email address of the recipient"
    )
