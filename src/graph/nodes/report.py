"""
Report generation node for the Real Estate Agent graph.

This node handles generating comprehensive reports based on SQL results,
context, and user questions. It uses centralized Redis caching for query results.
"""

import re
from typing import Dict, Any

from langchain_openai import ChatOpenAI

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from cache import cache_manager
from ..state import State


class ReportGenerationService:
    """Service for generating comprehensive real estate reports."""
    
    def __init__(self):
        """Initialize the report generation service."""
        self.llm = ChatOpenAI(
            model_name=config.llm.model_name,
            temperature=config.llm.temperature,
            streaming=config.llm.streaming,
            api_key=config.llm.api_key
        )
    
    def generate_report(self, state: State) -> State:
        """
        Generate a comprehensive report based on the current state.
        
        Args:
            state: Current graph state
            
        Returns:
            Generated report content
        """
        # Detect email request from user's question
        question = state.get("question", "")
        needs_email = bool(re.search(r"\b(email|mail|send)\b", question, re.I))
        print(f"DEBUG: Report node - Question: {question}")
        print(f"DEBUG: Report node - Email detection result: {needs_email}")
        
        # Build system prompt
        system_prompt = """You are a professional real estate analyst. Create a comprehensive, 
                well-formatted report based on the property data provided by user query , 
                property data results, and additional column context.

                ##Guidelines for your report:
                - Start with a Tabular Data metrics.
                - Highlight top 10 properties in a table if available
                - Include key statistics (average prices, property counts, etc.)
                - Highlight interesting trends or patterns
                - Provide actionable insights for buyers/sellers
                - Format data in tables or bullet points for readability
                - Add relevant real estate context and market insights

                **Ensure the report references the correct year based on the query results (e.g.,current year is 2025, last year is 2024)**
                
                **Suggest follow-up questions or additional searches**

                Make the report professional but accessible to general consumers.
                
                ## Guidelines for email:
                If the user requested the report via email, format it as a concise email:
                - Never say I'm unable to send emails.
                - Start with a polite greeting
                - Summarize key findings in the body.
                - End with a courteous closing."""
        
        # Compose the LLM input
        llm_input = [{"role": "system", "content": system_prompt}] + state["messages"]
        
        if state.get("sql_result"):
            llm_input.append({
                "role": "system", 
                "content": f"SQL result:\n{state['sql_result']} \nColumn context:{state['context']}"
            })
        
        # Call the model
        resp = self.llm.invoke(llm_input)
        state["email_state"] = needs_email
        report_content = getattr(resp, "content", str(resp))

        state["report"] = report_content
        state["needs_email"] = needs_email
        state["email_state"] = needs_email
        
        # Debug: Print what we're generating
        print(f"DEBUG: Report node - Generated report length: {len(report_content)}")
        print(f"DEBUG: Report node - Needs email: {needs_email}")
        print(f"DEBUG: Report node - Report preview: {report_content[:200]}...")
        
        return state


# Global report generation service instance
report_generation_service = ReportGenerationService()


def node_report_writer(state: State) -> State:
    """
    Generate final report based on SQL results and context.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with generated report
    """
    query = state.get("question", "")
    
    # Check for cached query result using centralized cache manager
    cached_result = cache_manager.get_json("query_cache", query)
    
    if cached_result and cached_result.get("report"):
        print("DEBUG: Using cached query result")
        state["question"] = cached_result.get("question", state.get("question"))
        state["context"] = cached_result.get("context", state.get("context"))
        state["llm_sql"] = cached_result.get("llm_sql", state.get("llm_sql"))
        state["sql_result"] = cached_result.get("sql_result", state.get("sql_result"))
        state["report"] = cached_result.get("report", state.get("report"))
        
        # Always check current question for email requests, don't use cached needs_email
        current_question = state.get("question", "")
        needs_email = bool(re.search(r"\b(email|mail|send)\b", current_question, re.I))
        state["needs_email"] = needs_email
        state["email_state"] = needs_email
        
        print(f"DEBUG: Cached result - Current question: {current_question}")
        print(f"DEBUG: Cached result - Email detection: {needs_email}")
        
        return state
    
    # Generate report and update state
    state = report_generation_service.generate_report(state)
    
    # Only add to messages if not going to email
    if not state.get("needs_email", False):
        state["messages"].append({"role": "assistant", "content": state["report"]})
        # Keep only last 10 messages to prevent memory issues
        state["messages"] = state["messages"][-10:]
    
    # Cache the query result using centralized cache manager
    result_data = {
        "question": state.get("question"),
        "context": state.get("context"),
        "llm_sql": state.get("llm_sql"),
        "sql_result": state.get("sql_result"),
        "report": state.get("report"),
        "needs_email": state.get("needs_email"),
        "email_state": state.get("email_state", None),
    }
    
    # Use centralized cache manager with 1 hour TTL for query results
    cache_manager.set_json("query_cache", query, result_data, ttl=3600)
    
    return state