"""
Main application module for the Real Estate Agent.

This module wires together the LangGraph workflow and provides the main
application interface for the real estate analysis system.
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from .conditions import need_sql, should_end, need_email
from .nodes.retrieve import node_retrieve
from .nodes.rewrite import node_rewrite_query
from .nodes.sql_write import node_write_sql_query
from .nodes.sql_run import node_run_sql
from .nodes.report import node_report_writer
from .nodes.email import node_email_report


def build_app() -> StateGraph:
    """
    Build and configure the Real Estate Agent LangGraph application.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    graph = StateGraph(State)
    
    # Set entry point
    graph.set_entry_point("retrieve")
    
    # Add nodes
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("rewrite_query", node_rewrite_query)
    graph.add_node("plan_sql", node_write_sql_query)
    graph.add_node("run_sql", node_run_sql)
    graph.add_node("report", node_report_writer)
    graph.add_node("email", node_email_report)
    
    # Add edges
    graph.add_edge("retrieve", "rewrite_query")
    graph.add_edge("rewrite_query", "plan_sql")
    
    # Conditional edges for SQL execution
    graph.add_conditional_edges(
        "plan_sql", 
        need_sql, 
        {"yes": "run_sql", "no": "report"}
    )
    
    # Edge from SQL execution to report
    graph.add_edge("run_sql", "report")
    
    # Conditional edges for email or end
    graph.add_conditional_edges(
        "report",
        should_end,
        {"email": "email", "END": END}
    ) 
    
    # Edge from email to end
    graph.add_edge("email", END)
    
    # Compile with memory
    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)
    
    return app

# Global app instance
app = build_app()
