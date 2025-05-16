import json
import re
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from app.dependencies import model, search, memory, create_retrieval_tool
import logging
import sys
import os
from typing import Dict, Any
from app.dependencies import transaction_tool

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def chat_stream(data: str, conversation_id: str = "accountant", file_messages: list = []):
    """Handles streaming chat responses from LangChain."""

    logger.info(f"Processing chat message for conversation: {conversation_id}")
    
    
    # Continue with regular chat processing
    # Check if message contains stress data from a video response
    contains_stress_data = any("stress indicators" in msg for msg in file_messages)
    if contains_stress_data:
        logger.info("Message contains stress analysis data")

    config = {"configurable": {"thread_id": conversation_id}}
    tools = [transaction_tool]
    agent_executor = create_react_agent(
        model, tools, checkpointer=memory, 
        prompt=SystemMessage(
"""
You are a master accountant specializing in income statements and financial transactions. Your main role is to help users add and classify financial transactions correctly.

When a user mentions a transaction, identify the key components and use the add_transaction tool to record it. Be helpful, polite, and patient with users who may not understand accounting terminology.

The add_transaction tool requires the following information:
- date: Transaction date in YYYY-MM-DD format if they give in some other format pls figure out what they mean.
- description: Clear description of what the transaction was for if its not present let the user know 
- amount: The dollar amount (positive number)
- category: The specific category the transaction belongs to
- transaction_type: Must be one of: 'revenue', 'expense', 'cost_of_sales', or 'inventory'

Guidelines for classifying transactions:
1. Revenue: Money earned from selling products or services (sales, fees, commissions)
2. Cost of Sales: Direct costs of products/services sold (inventory purchases, raw materials, manufacturing labor)
3. Expense: Operating costs not directly tied to product creation (rent, utilities, salaries, marketing)
4. Inventory: Items purchased for resale that haven't been sold yet

If the user doesn't provide complete transaction information, politely ask for the missing details before adding the transaction.

Examples of categories:
- Revenue: Sales, Services, Interest Income, Commissions
- Cost of Sales: Plus goods purchased or manufactured, Direct Labor
- Expenses: Rent, Utilities, Payroll, Marketing, Office Supplies

Please confirm each transaction after it's been added and offer assistance with any other accounting needs. Let the user know if a transaction doesn't need to be added to the income statement.
"""
        )
    )

    try:
        # Log the system messages that will be passed to the LLM
        for msg in file_messages:
            logger.info(f"System message: {msg[:100]}...")
        
        # Stream the response
        async for chunk in agent_executor.astream({"messages": file_messages + [
            HumanMessage(content=data)
        ]}, config):
            for key in chunk:
                for message in chunk[key]['messages']:
                    yield json.dumps({"role": key, "message": message.content, "conversation_id": conversation_id}) + "\n"
        
        logger.info(f"Response generation completed for conversation: {conversation_id}")
    except Exception as e:
        logger.error(f"Error in chat_stream: {e}", exc_info=True)
        yield json.dumps({"error": str(e)}) + "\n"