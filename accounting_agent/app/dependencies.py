from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver
from app.config import settings
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.tools import Tool


# Setup LangChain Agent
memory = MemorySaver()
model = ChatGoogleGenerativeAI(
    model=settings.GOOGLE_MODEL, 
    temperature=settings.TEMPERATURE, 
)
search = DuckDuckGoSearchRun(max_results=2)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
vectorstore = Chroma(
    collection_name="main_collection", persist_directory="shared_chroma_db", embedding_function=embeddings)

def create_retrieval_tool(conversation_id: str):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"filter": {"conversation_id": conversation_id}, "k": 10},
    )


    # search_kwargs={"filter": {"conversation_id": conversation_id}, "k": 10},  # Increase k


    def vectorstore_retrieval(query: str) -> str:
        """Retrieves relevant documents from the vectorstore based on the query."""
        results = retriever.invoke(query)
        formatted_results = []
        
        for i, doc in enumerate(results):
            formatted_results.append(f"--- Document Chunk {i+1} ---\n{doc.page_content}\n")
            
        return "\n".join(formatted_results)
    retrieval_tool = Tool(
        name="vectorstore_retrieval",
        func=vectorstore_retrieval,
        description="Useful for answering questions about information stored in the vectorstore. Input should be a fully formed question.",
    )

    return retrieval_tool
