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
        # Detect email request from user's question - more precise detection
        question = state.get("question", "")
        # Look for explicit email requests with more specific patterns
        email_patterns = [
            r"\b(send|email|mail)\s+(me|to\s+me|the\s+report)\b",
            r"\b(report|analysis|data)\s+(to\s+)?(my\s+)?email\b",
            r"\bemail\s+(me|the\s+report|it)\b",
            r"\bsend\s+(it|the\s+report|this)\s+(to\s+)?(my\s+)?email\b"
        ]
        needs_email = any(re.search(pattern, question, re.I) for pattern in email_patterns)
        print(f"DEBUG: Report node - Question: {question}")
        print(f"DEBUG: Report node - Email detection result: {needs_email}")
        
        # Build system prompt - conditional based on email request
        if needs_email:
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
                    Since the user requested the report via email, format it as a concise email:
                    - Never say I'm unable to send emails.
                    - Start with a polite greeting
                    - Summarize key findings in the body.
                    - End with a courteous closing."""
        else:
            system_prompt = """You are a professional real estate analyst and helpful assistant. You can handle both real estate queries and general conversations.

                                ## For Real Estate Queries:
                                When the user asks about properties, market data, or real estate analysis:
                                - Create a comprehensive, well-formatted report based on the property data provided
                                - Start with Tabular Data metrics
                                - Highlight top 10 properties in a table if available
                                - Include key statistics (average prices, property counts, etc.)
                                - Highlight interesting trends or patterns
                                - Provide actionable insights for buyers/sellers
                                - Format data in tables or bullet points for readability
                                - Add relevant real estate context and market insights
                                - Ensure the report references the correct year based on the query results (e.g., current year is 2025, last year is 2024)
                                - Suggest follow-up questions or additional searches
                                - Make the report professional but accessible to general consumers

                                ## For General Questions (Greetings, Introductions, General Inquiries):
                                When the user asks general questions like greetings, introductions, or "what can you do":
                                - Respond in a friendly, professional manner
                                - Introduce yourself as a Real Estate AI Assistant
                                - Explain your capabilities: property analysis, market insights, data visualization, email reports
                                - Provide examples of what you can help with
                                - Keep responses concise and engaging
                                - Guide users toward real estate-related questions when appropriate

                                ## Examples of General Responses:
                                - "Hello! I'm your Real Estate AI Assistant. I can help you analyze property data, find market insights, and generate comprehensive reports. What would you like to know about real estate?"
                                - "I'm doing great! I'm here to help you with all your real estate needs. I can analyze property listings, provide market statistics, and even send detailed reports to your email. What can I help you with today?"
                                - "I can help you with property analysis, market trends, price comparisons, and much more. Just ask me about properties in any area, and I'll provide detailed insights!"

                                ## Guidelines for Email:
                                If the user requested the report via email, format it as a concise email:
                                - Never say I'm unable to send emails
                                - Start with a polite greeting
                                - Summarize key findings in the body
                                - End with a courteous closing

                                IMPORTANT: Do NOT format general conversations as emails. Only format real estate reports as emails when explicitly requested."""
        
        # Compose the LLM input
        llm_input = [{"role": "system", "content": system_prompt}] + state["messages"]
        
        if state.get("sql_result"):
            context_str = "\n".join(state.get("context", [])) if isinstance(state.get("context"), list) else str(state.get("context", ""))
            llm_input.append({
                "role": "system", 
                "content": f"SQL result:\n{state['sql_result']} \nColumn context: {context_str}"
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
        # Use the same improved email detection logic
        email_patterns = [
            r"\b(send|email|mail)\s+(me|to\s+me|the\s+report)\b",
            r"\b(report|analysis|data)\s+(to\s+)?(my\s+)?email\b",
            r"\bemail\s+(me|the\s+report|it)\b",
            r"\bsend\s+(it|the\s+report|this)\s+(to\s+)?(my\s+)?email\b"
        ]
        needs_email = any(re.search(pattern, current_question, re.I) for pattern in email_patterns)
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