"""
Retrieval node for the Real Estate Agent graph.

This node handles context retrieval from the vector store using similarity search.
"""

import json
from typing import List
from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from cache import cache_manager
from ..state import State


class RetrievalService:
    """Service for handling document retrieval from vector store."""
    
    def __init__(self):
        """Initialize the retrieval service."""
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.embedding.model_name
        )
        self.vector_store = PGVector(
            connection=config.database.connection_string,
            embeddings=self.embeddings,
            collection_name=config.collection_name,
            use_jsonb=config.use_jsonb,
        )
    
    def retrieve_context(self, query: str, k: int = 1) -> List[str]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The search query
            k: Number of documents to retrieve
            
        Returns:
            List of relevant document contents
        """
        # Try cache first
        cached = cache_manager.get_json("similarity", query)
        if cached:
            try:
                docs = [
                    Document(
                        page_content=item["page_content"], 
                        metadata=item.get("metadata", {})
                    ) 
                    for item in cached
                ]
                return [d.page_content for d in docs]
            except (KeyError, TypeError):
                # Fall through to real search on parse error
                pass
        
        # Perform similarity search
        docs = self.vector_store.similarity_search(query, k=k)
        context = [d.page_content for d in docs]
        
        # Cache the results
        try:
            serializable = [
                {
                    "page_content": d.page_content, 
                    "metadata": d.metadata
                } 
                for d in docs
            ]
            cache_manager.set_json("similarity", query, serializable)
        except Exception:
            pass
        
        return context


# Global retrieval service instance
retrieval_service = RetrievalService()


def node_retrieve(state: State) -> State:
    """
    Retrieve context from vector store and update state.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with context information
    """
    query = state.get("question", "")
    context = retrieval_service.retrieve_context(query)
    
    return {
        **state, 
        "context": context
    }
