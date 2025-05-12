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

# Add this import (after creating the file)
from app.services.income_statement_service import process_income_statement_request

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_income_statement_request(message: str) -> bool:
    """Check if the message is requesting an income statement update."""
    keywords = ["income statement", "profit and loss", "p&l", "financial statement"]
    transaction_indicators = ["transaction", "sold", "purchased", "paid", "received", "$"]
    
    return (any(keyword in message.lower() for keyword in keywords) and 
            any(indicator in message.lower() for indicator in transaction_indicators))

async def chat_stream(data: str, conversation_id: str = "accountant", file_messages: list = []):
    """Handles streaming chat responses from LangChain."""

    logger.info(f"Processing chat message for conversation: {conversation_id}")
    
    # Check if message is an income statement request
    if is_income_statement_request(data):
        logger.info("Processing income statement request")
        try:
            # Process income statement request
            result = process_income_statement_request(data, conversation_id)
            
            if result['success']:
                response = {
                    "role": "assistant",
                    "message": f"I've updated the income statement for {result['business_name']} covering {result['date_range']}.\n\n{result['statement']}",
                    "conversation_id": conversation_id,
                    "income_statement_data": result
                }
                yield json.dumps(response) + "\n"
            else:
                response = {
                    "role": "assistant",
                    "message": f"I couldn't process the income statement request: {result['error']}",
                    "conversation_id": conversation_id
                }
                yield json.dumps(response) + "\n"
            
            logger.info("Income statement processing completed")
            return
        except Exception as e:
            logger.error(f"Error in income statement processing: {e}", exc_info=True)
            # Fall back to regular chat processing if income statement fails
    
    # Continue with regular chat processing
    # Check if message contains stress data from a video response
    contains_stress_data = any("stress indicators" in msg for msg in file_messages)
    if contains_stress_data:
        logger.info("Message contains stress analysis data")

    config = {"configurable": {"thread_id": conversation_id}}
    tools = [search, create_retrieval_tool(conversation_id)]
    agent_executor = create_react_agent(
        model, tools, checkpointer=memory, 
        prompt=SystemMessage(
"""
You are a master accountant specializing in financial statements and transaction classification.

When analyzing transactions for income statements:

1. **Transaction Types**:
   - Revenue: Money earned from sales of goods/services (Sales, Service Fees, Commissions)
   - Cost of Sales: Direct costs tied to revenue generation (Inventory, Raw Materials, Manufacturing Labor)
   - Expenses: Operational costs not directly tied to production (Rent, Utilities, Salaries, Marketing)

2. **Subcategories**:
   - Revenue: Sales, Services, Interest Income, Other Income
   - Cost of Sales: Beginning Inventory, Purchases, Manufacturing Costs, Less Ending Inventory
   - Expenses: Rent, Utilities, Payroll, Insurance, Marketing, Office Supplies, Depreciation

3. **When classifying transactions**:
   - Look for key verbs: "sold" (Revenue), "purchased inventory" (Cost of Sales), "paid for" (likely Expense)
   - Consider if the cost directly contributes to creating products/services
   - Check for recurring operational costs (typically Expenses)

4. **Your response format**:
   - Clearly state the transaction type and subcategory
   - Explain your reasoning briefly
   - When processing multiple transactions, organize them in a structured list
   - Calculate subtotals for each category when appropriate

For income statement generation requests, I'll parse transactions and categorize them appropriately following accounting principles.
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