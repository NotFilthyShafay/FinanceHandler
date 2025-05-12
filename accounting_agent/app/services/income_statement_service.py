import sys
import os
import re
from datetime import datetime
from typing import List, Dict, Any

# Add income_statement directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../income_statement')))
from income_statement import IncomeStatement, Transaction

def process_income_statement_request(message: str, conversation_id: str = None) -> Dict[str, Any]:
    """Process a natural language request to create/update an income statement"""
    try:
        # Extract business details
        business_match = re.search(r'(?:for|business name:?|company:?) ([^,\.]+)', message, re.IGNORECASE)
        business_name = business_match.group(1).strip() if business_match else "My Business"
        
        # Extract date range
        date_range_match = re.search(r'(?:from|between) (\w+ \d{1,2},? \d{4}) (?:to|and|through) (\w+ \d{1,2},? \d{4})', message, re.IGNORECASE)
        if date_range_match:
            try:
                start_date = datetime.strptime(date_range_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
                end_date = datetime.strptime(date_range_match.group(2), "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    start_date = datetime.strptime(date_range_match.group(1), "%B %d %Y").strftime("%Y-%m-%d")
                    end_date = datetime.strptime(date_range_match.group(2), "%B %d %Y").strftime("%Y-%m-%d")
                except ValueError:
                    today = datetime.now()
                    start_date = f"{today.year}-{today.month:02d}-01"
                    end_date = f"{today.year}-{today.month:02d}-{today.day:02d}"
        else:
            today = datetime.now()
            start_date = f"{today.year}-{today.month:02d}-01"
            end_date = f"{today.year}-{today.month:02d}-{today.day:02d}"
            
        # Extract inventory information
        inventory_match = re.search(r'beginning inventory[: ]?[\$]?(\d+(?:,\d+)*(?:\.\d+)?)', message, re.IGNORECASE)
        beginning_inventory = 0
        if inventory_match:
            beginning_inventory = float(inventory_match.group(1).replace(',', ''))
        
        ending_match = re.search(r'ending inventory[: ]?[\$]?(\d+(?:,\d+)*(?:\.\d+)?)', message, re.IGNORECASE)
        ending_inventory = None
        if ending_match:
            ending_inventory = float(ending_match.group(1).replace(',', ''))
        
        # Create income statement
        income_statement = IncomeStatement(business_name, start_date, end_date, beginning_inventory)
        
        if ending_inventory is not None:
            income_statement.set_ending_inventory(ending_inventory)
        
        # Extract transactions
        transaction_texts = []
        if "transactions:" in message.lower():
            transactions_section = message.lower().split("transactions:")[1]
            for delimiter in ['\n', ';']:
                if delimiter in transactions_section:
                    transaction_texts = [t.strip() for t in transactions_section.split(delimiter) if t.strip()]
                    break
        else:
            # Try to find transaction patterns
            transaction_patterns = [
                r'(?:sold|purchased|paid|received|bought) .+? for \$\d+',
                r'\$\d+ (?:for|on|to) .+?(?:\.|$)',
            ]
            
            for pattern in transaction_patterns:
                matches = re.finditer(pattern, message, re.IGNORECASE)
                for match in matches:
                    transaction_texts.append(match.group(0))
        
        # Parse and add transactions
        transactions = []
        for text in transaction_texts:
            transaction = parse_transaction(text)
            if transaction:
                income_statement.add_transaction(transaction)
                transactions.append({
                    'date': transaction.date,
                    'description': transaction.description,
                    'amount': transaction.amount,
                    'category': transaction.category,
                    'transaction_type': transaction.transaction_type
                })
        
        # Generate statement text
        statement_text = income_statement.generate_statement()
        
        # Export to Excel if requested
        excel_path = None
        if "excel" in message.lower() or "export" in message.lower():
            os.makedirs("output", exist_ok=True) 
            excel_path = f"output/income_statement_{conversation_id}.xlsx"
            income_statement.export_to_excel(excel_path)
            
        return {
            'success': True,
            'statement': statement_text,
            'excel_path': excel_path,
            'transactions_processed': len(transactions),
            'transactions': transactions,
            'business_name': business_name,
            'date_range': f"{start_date} to {end_date}"
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def parse_transaction(text: str) -> Transaction:
    """Parse natural language into a Transaction object"""
    try:
        # Extract date (default to today if not found)
        date_match = re.search(r'(?:on|dated) ([A-Za-z]+ \d{1,2},? \d{4})', text)
        if date_match:
            try:
                date_str = date_match.group(1)
                date = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    date = datetime.strptime(date_str, "%B %d %Y").strftime("%Y-%m-%d")
                except ValueError:
                    date = datetime.now().strftime("%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Extract amount
        amount_match = re.search(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', text)
        amount = 0.0
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            amount = float(amount_str)
        
        # Determine transaction type and category
        transaction_type = "expense"  # Default
        if any(word in text.lower() for word in ["sold", "sale", "revenue", "income", "received", "payment"]):
            transaction_type = "revenue"
            category = determine_revenue_category(text)
        elif any(word in text.lower() for word in ["inventory", "stock", "goods", "merchandise", "purchased"]):
            transaction_type = "cost_of_sales"
            category = "Plus goods purchased or manufactured"
        else:
            category = determine_expense_category(text)
        
        description = text[:50] + ("..." if len(text) > 50 else "")
        
        return Transaction(date, description, amount, category, transaction_type)
    except Exception as e:
        print(f"Error parsing transaction: {e}")
        return None

def determine_revenue_category(text: str) -> str:
    if any(word in text.lower() for word in ["service", "consulting", "hourly"]):
        return "Services"
    return "Sales"

def determine_expense_category(text: str) -> str:
    text_lower = text.lower()
    categories = {
        "Rent": ["rent", "lease", "office space"],
        "Utilities": ["utilities", "electricity", "water", "gas", "internet", "phone"],
        "Payroll": ["salary", "salaries", "wage", "wages", "payroll", "employee", "staff"],
        "Marketing": ["marketing", "advertising", "promotion", "campaign"],
        "Supplies": ["supplies", "office supplies", "materials"],
        "Equipment": ["equipment", "machinery", "device", "computer", "furniture"],
    }
    
    for category, keywords in categories.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    
    return "Other Expenses"