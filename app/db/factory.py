"""
Factory for creating vector store instances.
"""
from langchain_openai import OpenAIEmbeddings

from app.db.vector_store import AsyncPgVector, ExtendedPgVector


def get_vector_store(
    connection_string: str,
    embeddings: OpenAIEmbeddings,
    collection_name: str,
    mode: str = "sync",
) -> ExtendedPgVector | AsyncPgVector:
    """
    Factory function to create vector store instances.

    TODO: Implement this factory to return appropriate vector store based on mode.
    - If mode is "sync", return ExtendedPgVector
    - If mode is "async", return AsyncPgVector
    - Raise ValueError for invalid mode

    Args:
        connection_string: Database connection string
        embeddings: Embedding function to use
        collection_name: Name of the collection
        mode: "sync" or "async"

    Returns:
        Vector store instance
    """
    if mode == "sync":
        return ExtendedPgVector(
            connection_string=connection_string,
            embedding_function=embeddings,
            collection_name=collection_name,
        )
    elif mode == "async":
        return AsyncPgVector(
            connection_string=connection_string,
            embedding_function=embeddings,
            collection_name=collection_name,
        )
    else:
        raise ValueError("Invalid mode specified. Choose 'sync' or 'async'.")
