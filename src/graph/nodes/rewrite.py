"""
Query rewriting node for the Real Estate Agent graph.

This node handles rewriting user queries to make them more precise and suitable
for SQL generation by replacing vague terms with specific values.
"""

from langchain_openai import ChatOpenAI

import sys
import os
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from ..state import State


class QueryRewritingService:
    """Service for rewriting user queries to be more precise."""
    
    def __init__(self):
        """Initialize the query rewriting service."""
        self.llm = ChatOpenAI(
            model_name=config.llm.model_name,
            temperature=config.llm.temperature,
            streaming=config.llm.streaming,
            api_key=config.llm.api_key
        )
    
    def rewrite_query(self, original_query: str) -> str:
        """
        Rewrite a user query to make it more precise.
        
        Args:
            original_query: The original user query
            
        Returns:
            Rewritten query with specific terms
        """
        prompt = f"""You are a query rewriting assistant. Rewrite the user's query to make it precise and suitable for SQL generation.
        - Replace vague terms like 'this year' with the current year (2025).
        - Replace 'last year' with the previous year (2024).
        - Ensure the query is clear and unambiguous.
        - Return only the rewritten query, no explanations.

        Query: {original_query}
        Rewritten query:"""

        try:
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            return response.content.strip()
        except Exception as e:
            print(f"Error rewriting query: {e}")
            return original_query


# Global query rewriting service instance
query_rewriting_service = QueryRewritingService()


def node_rewrite_query(state: State) -> State:
    """
    Rewrite the user query using the LLM.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with rewritten query
    """
    original_query = state.get("question", "")
    email_patterns = [
        r"\b(send|email|mail)\s+(me|to\s+me|the\s+report)\b",
        r"\b(report|analysis|data)\s+(to\s+)?(my\s+)?email\b", 
        r"\bemail\s+(me|the\s+report|it)\b",
        r"\bsend\s+(it|the\s+report|this)\s+(to\s+)?(my\s+)?email\b"
    ]
    is_email_request = any(re.search(pattern, original_query, re.I) for pattern in email_patterns)
    
    if is_email_request:
        # For email requests, don't rewrite the query - keep original for email detection
        print(f"DEBUG: Rewrite node - Email request detected, keeping original query")
        return {
            **state,
            "question": original_query  # Keep original query for email detection
        }
    else:
        rewritten_query = query_rewriting_service.rewrite_query(original_query)
        
        return {
            **state,
            "question": rewritten_query
        }
