from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import MemorySaver
from app.config import settings
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.tools import Tool
from income_statement.income_statement import Transaction, IncomeStatement
import datetime

import datetime
current_datetime = datetime.datetime.now()

# Global transactions list
transactions = []

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

def add_transaction(date: str, description: str, amount: float, category: str, transaction_type: str) -> str:
    """
    Adds a transaction to the income statement and regenerates the Excel report.

    Args:
        date: Transaction date in YYYY-MM-DD format
        description: Description of the transaction
        amount: Transaction amount (positive number)
        category: Category of the transaction
        transaction_type: Type of transaction ('revenue', 'expense', 'cost_of_sales', or 'inventory')
        
    Returns:
        A message confirming the transaction was added and the income statement was updated
    """
    # Validate transaction_type
    valid_types = ['revenue', 'expense', 'cost_of_sales', 'inventory']
    if transaction_type not in valid_types:
        return f"Error: transaction_type must be one of {valid_types}"
    
    # Create and add new transaction
    try:
        new_transaction = Transaction(date , description, float(amount), category, transaction_type)
        transactions.append(new_transaction)
        
        # Create income statement with all transactions
        income_statement = IncomeStatement("Jacko's Business", "2025-01-01", "2025-12-31", beginning_inventory=2000.00)
        income_statement.set_ending_inventory(1500.00)  # This could be made configurable
        income_statement.add_transactions(transactions)
        
        # Export to Excel, overwriting previous file
        excel_file = income_statement.export_to_excel("output/income_statement.xlsx")
        
        return f"Transaction added successfully. Total transactions: {len(transactions)}. Income statement updated at {excel_file}"
    except Exception as e:
        return f"Error: {str(e)}"

# Create a Tool for the LLM to use
# transaction_tool = Tool(
#     name="add_transaction",
#     func=add_transaction,
#     description="Adds a financial transaction to the income statement and updates the Excel report. "
#                 "Requires date (YYYY-MM-DD), description, amount, category, and transaction_type "
#                 "('revenue', 'expense', 'cost_of_sales', or 'inventory')",
# )

transaction_tool = add_transaction

def create_retrieval_tool(conversation_id: str):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"filter": {"conversation_id": conversation_id}, "k": 10},
    )

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
