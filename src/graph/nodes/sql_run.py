"""
SQL execution node for the Real Estate Agent graph.

This node handles executing SQL queries against the database and storing
the results in the state.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.services.db.sql import run_sql
from ..state import State


def node_run_sql(state: State) -> State:
    """
    Execute the SQL query and store results.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with SQL execution results
    """
    if not state.get("llm_sql"):
        return {**state, "sql_result": "No SQL query to execute"}
    
    try:
        result = run_sql(state["llm_sql"])
        return {**state, "sql_result": result}
    except Exception as e:
        print(f"SQL Execution Error: {e}")
        return {**state, "sql_result": f"SQL execution error: {str(e)}"}
