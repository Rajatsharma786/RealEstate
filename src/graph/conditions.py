"""
Conditional logic for the Real Estate Agent LangGraph.

This module contains the conditional functions that determine the flow
of execution through the graph based on the current state.
"""

from typing import Literal
from .state import State


def need_sql(state: State) -> Literal["yes", "no"]:
    """
    Determine if SQL generation and execution is needed.
    
    Args:
        state: Current graph state
        
    Returns:
        "yes" if SQL is needed, "no" otherwise
    """
    return "yes" if state.get("needs_sql", False) else "no"


def need_email(state: State) -> Literal["yes", "no"]:
    """
    Determine if the report needs to be emailed.
    
    Args:
        state: Current graph state
        
    Returns:
        "yes" if email is needed, "no" otherwise
    """
    return "yes" if state.get("needs_email", False) else "no"


def should_end(state: State) -> Literal["email", "END"]:
    """
    Determine if the graph should continue to email or end.
    
    Args:
        state: Current graph state
        
    Returns:
        "email" if email is needed, "END" to terminate the graph
    """
    needs_email = state.get("needs_email", False)
    print(f"DEBUG: should_end condition - needs_email: {needs_email}")
    print(f"DEBUG: should_end condition - state keys: {list(state.keys())}")
    return "email" if needs_email else "END"
