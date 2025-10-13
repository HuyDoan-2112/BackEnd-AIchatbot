"""
RAG (Retrieval-Augmented Generation) service for chat functionality.
"""
from typing import Union

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.db.vector_store import AsyncPgVector, ExtendedPgVector


class RAGService:
    """Service for RAG-based question answering."""

    def __init__(
        self,
        vector_store: Union[ExtendedPgVector, AsyncPgVector],
        model_name: str = "openai/gpt-oss-20b"
    ):
        self.vector_store = vector_store
        self.retriever = vector_store.as_retriever()
        self.chain = self._build_chain(model_name)

    def _build_chain(self, model_name: str):
        """
        Build the RAG chain.

        TODO: Implement this method to build the LangChain RAG chain.
        - Create prompt template for question answering
        - Initialize ChatOpenAI model
        - Build chain with retriever, prompt, model, and output parser
        - Return the chain
        """
        template = """Answer the question based only on the following context:
        {context}

        Question: {question}"""

        prompt = ChatPromptTemplate.from_template(template)
        model = ChatOpenAI(model_name=model_name)

        chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | prompt
            | model
            | StrOutputParser()
        )

        return chain

    async def get_response(self, question: str) -> str:
        """
        Get RAG response for a question.

        TODO: Implement this method to generate answers.
        - Invoke the chain with the question
        - Handle both sync and async invocation
        - Return the generated response
        """
        result = self.chain.invoke(question)
        return result
