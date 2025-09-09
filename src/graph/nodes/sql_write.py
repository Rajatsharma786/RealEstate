"""
SQL generation node for the Real Estate Agent graph.

This node handles generating SQL queries from user questions using the LLM
with proper schema information and context.
"""

from langchain_openai import ChatOpenAI

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from src.services.db.sql import get_schema_info
from ..state import State, State_Output


class SQLGenerationService:
    """Service for generating SQL queries from natural language."""
    
    def __init__(self):
        """Initialize the SQL generation service."""
        self.llm = ChatOpenAI(
            model_name=config.llm.model_name,
            temperature=config.llm.temperature,
            streaming=config.llm.streaming,
            api_key=config.llm.api_key
        )
    
    def create_sql_prompt(self, user_query: str, schema: str, context: list) -> str:
        """
        Create the SQL generation prompt with proper variable substitution.
        
        Args:
            user_query: The user's question
            schema: Database schema information
            context: Additional context from retrieval
            
        Returns:
            Formatted prompt for SQL generation
        """
        context_str = "\n".join(context) if context else "No additional context provided."
        
        return f"""You are PostgreSQL-Master. You write correct, safe PostgreSQL queries.

        USER_QUERY: {user_query}
        SCHEMA: {schema}
        COLUMN_CONTEXT: {context_str}

        ##Instructions:
        - PostgreSQL dialect only.
        - Do not invent tables/columns. If something is missing or ambiguous, ask for clarification.
        - No SELECT *; qualify columns with aliases in joins.
        - Use proper data types based on the schema provided.
        - Include deterministic ORDER BY when using LIMIT.
        - Read-only queries only (no DROP, ALTER, INSERT, UPDATE, DELETE, CREATE).
        - For time queries: if the year is not specified in the USER_QUERY, default to filtering for the current year (2025).

        ##Schema Available:
        {schema}

        ##Examples for Real Estate Queries:
        Example 1
        USER_QUERY: "Houses in VIC state listed this year with at least 2 bedrooms"
        Expected: SELECT address, price, bedrooms, suburb FROM properties WHERE state = 'VIC' AND bedrooms >= 2 AND date_part('year', date_of_property_listed) = 2025 ORDER BY price DESC LIMIT 50;

        Example 2  
        USER_QUERY: "Average price by suburb in VIC"
        Expected: SELECT suburb, AVG(price) as avg_price, COUNT(*) as property_count FROM properties WHERE state = 'VIC' GROUP BY suburb ORDER BY avg_price DESC;

        ##Your Task:
        Generate a single, clean SQL query based on the USER_QUERY and SCHEMA provided.
        Return ONLY the SQL query, no explanations."""
    
    def generate_sql(self, user_query: str, context: list) -> str:
        """
        Generate SQL query from user question and context.
        
        Args:
            user_query: The user's question
            context: Additional context from retrieval
            
        Returns:
            Generated SQL query
        """
        try:
            schema = get_schema_info(include_types=True)
            prompt_content = self.create_sql_prompt(
                user_query=user_query,
                schema=schema, 
                context=context
            )
            
            messages = [
                {"role": "system", "content": prompt_content},
                {"role": "user", "content": f"Generate SQL for: {user_query}"}
            ]
            
            response = self.llm.with_structured_output(State_Output).invoke(messages)
            return response.sql_query.strip() if hasattr(response, 'sql_query') else ""
            
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return ""


# Global SQL generation service instance
sql_generation_service = SQLGenerationService()


def node_write_sql_query(state: State) -> State:
    """
    Generate SQL query based on question, context, and schema.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with generated SQL query
    """
    sql_query = sql_generation_service.generate_sql(
        user_query=state["question"],
        context=state["context"]
    )
    
    return {
        **state,
        "llm_sql": sql_query,
        "needs_sql": bool(sql_query)
    }
