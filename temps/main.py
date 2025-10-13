import os

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from models import DocumentModel, DocumentResponse
from store import AsnyPgVector
from store_factory import get_vector_store

load_dotenv(find_dotenv())

app = FastAPI()

def get_env_variable (var_name: str) -> str:    
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} not found")
    return value

try:
    USE_ASYNC  = os.getenv("USE_ASYNC", "false").lower() == "true"
    if USE_ASYNC:
        print("Async project used")
    
    POSTGRES_DB = get_env_variable("POSTGRES_DB")
    POSTGRES_USER = get_env_variable("POSTGRES_USER")
    POSTGRES_PASSWORD = get_env_variable("POSTGRES_PASSWORD")
    DB_HOST = get_env_variable("DB_HOST")
    DB_PORT = get_env_variable("DB_PORT")

    CONNECTION_STRING = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"

    OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY")
    embeddings = OpenAIEmbeddings()

    mode = "async" if USE_ASYNC else "sync" 
    pgvector_store = get_vector_store( # Async vector store
        connection_string = CONNECTION_STRING,
        embeddings = embeddings,
        collection_name = "testcollection",
        mode = mode,
    )
    retriever = pgvector_store.as_retriever() #check over document or insert our API
    template = """Answer the question based only on the following context
    {context}
    
    Question: {question}"""

    prompt = ChatPromptTemplate.from_template(template)
    model = ChatOpenAI(model_name= "openai/gpt-oss-20b")
    chain = (
        {"context0:": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/add_document/")
async def add_document(documents: list[DocumentModel]):
    try:
        docs = [
            Document(
                page_content = doc.page_content,
                metadata = (
                    {**doc.metadata, "digest": doc.generate_digest()}
                    if doc.metadata
                    else {"digest": doc.generate_digest()}
                          
                ),
            ) for doc in documents
        ] 
        ids = (
            await pgvector_store.add_documments(docs)
            if isinstance(pgvector_store, AsnyPgVector)
            else pgvector_store.add_documments(docs) 
        )
        return {"message": "Documents added successfully", "ids":ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-all-ids/")
async def get_all_ids():
    try:
        if isinstance(pgvector_store, AsnyPgVector):
            ids = await pgvector_store.get_all_ids()
        else:
            ids = pgvector_store.get_all_ids()

        return ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/get-documents-by-ids/")
async def get_documents_by_ids(ids: list[str]):
    try:
        if isinstance(pgvector_store, AsnyPgVector):
            existing_ids = await pgvector_store.get_all_ids()
            documents = await pgvector_store.get_documents_by_ids(ids)
        else:
            existing_ids = pgvector_store.get_all_ids()
            DocumentResponse ( pgvector_store.get_documents_by_ids(ids))

        if not  all(id in existing_ids for id in ids):
            raise HTTPException(status_code=404, detail="One or more IDs not found")
        
        return documents
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/delete-documents/")
async def delete_documents(ids: list[str]):
    try:
        if isinstance(pgvector_store, AsnyPgVector):
            existing_ids = await pgvector_store.get_all_ids()
            await pgvector_store.delete_documents(ids=ids)
        else:
            existing_ids = pgvector_store.get_all_ids()
            pgvector_store.delete_documents(ids=ids)
        
        if not all(id in existing_ids for id in ids):
            raise HTTPException(status_code=404, detail="One or more IDs not found")
        

        return {"message": f"{len(ids)} documents deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.chat("/chat/")
async def quick_response(msg: str):
    result = chain.invoke(msg)
    return result