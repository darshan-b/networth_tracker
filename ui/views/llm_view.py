"""
Financial Chat Assistant using Ollama - Complete Fixed Version

IMPORTANT NOTES:
1. If you have ColumnNames defined elsewhere in your project:
   - Comment out the ColumnNames class below
   - Import it: from config.constants import ColumnNames

2. Net Worth Data Structure (LONG FORMAT):
   - Each row = ONE account's value on a specific date
   - Multiple rows exist for the same date (one per account)
   - Columns: account_type, category, account, month (date), amount
   
   Example:
   account_type  | category | account            | month      | amount
   Brokerage     | Taxable  | Fidelity          | 2024-12-01 | 1166.98
   Brokerage     | Taxable  | Charles Schwab    | 2024-12-01 | 954.21
   Checking      | Cash     | Chase Checking    | 2024-12-01 | 5000.00
   Credit Card   | Debt     | Amex              | 2024-12-01 | -2500.00
   
   Net Worth Calculation:
   - GROUP BY month (date)
   - SUM all amounts for that date
   - For 2024-12-01: 1166.98 + 954.21 + 5000.00 + (-2500.00) = $4,621.19
"""

import streamlit as st
import pandas as pd
import ollama
from datetime import datetime

# ================== COLUMN NAMES ==================
# If importing from elsewhere, comment this out and import instead:
# from config.constants import ColumnNames

class ColumnNames:
    """Standard column names used across the application."""
    # Expense columns
    DATE = 'date'
    MONTH = 'month'
    MONTH_STR = 'month_Str'
    AMOUNT = 'amount'
    CATEGORY = 'category'
    SUBCATEGORY = 'subcategory'
    MERCHANT = 'merchant'
    ACCOUNT = 'account'
    ACCOUNT_TYPE = 'account_type'
    
    # Net Worth columns (long format - one row per account per date)
    # Net worth is calculated by: GROUP BY date, SUM(amount)

# ================== CONTEXT GENERATION ==================

def create_financial_context(expenses_df, networth_df, include_samples=False, data_sources=['expenses', 'networth']):
    """
    Create context from financial data using proper column names
    
    Args:
        expenses_df: DataFrame with expense data
        networth_df: DataFrame with net worth data
        include_samples: Boolean to include sample transactions
        data_sources: List of data sources to include ('expenses', 'networth', or both)
    """
    context = """You are a helpful financial assistant having a conversation with a user about their finances.

IMPORTANT: 
- You have access to data based on what the user has selected
- Remember the conversation history and refer to previous messages when relevant
- If the user asks follow-up questions like "tell me more" or "what about that", refer to the previous context
- Be conversational and helpful
- Give specific numbers from the data when answering

"""
    
    # Track what data is available
    available_data = []
    if 'expenses' in data_sources:
        available_data.append("EXPENSE/SPENDING data")
    if 'networth' in data_sources:
        available_data.append("NET WORTH/ASSET data")
    
    if available_data:
        context += f"You have access to: {', '.join(available_data)}\n\n"
    
    context += "Here's the user's financial data:\n\n"
    
    # Only include expenses if selected
    if 'expenses' in data_sources and expenses_df is not None and len(expenses_df) > 0:
        context += """
==================================================
📊 EXPENSE & SPENDING DATA
==================================================
"""
        total = abs(expenses_df[ColumnNames.AMOUNT].sum())
        avg = abs(expenses_df[ColumnNames.AMOUNT].mean())
        days = (expenses_df[ColumnNames.DATE].max() - expenses_df[ColumnNames.DATE].min()).days + 1
        
        context += "=== EXPENSE SUMMARY ===\n"
        context += f"• Total Transactions: {len(expenses_df):,}\n"
        context += f"• Date Range: {expenses_df[ColumnNames.DATE].min().strftime('%Y-%m-%d')} to {expenses_df[ColumnNames.DATE].max().strftime('%Y-%m-%d')}\n"
        context += f"• Total Spending: ${total:,.2f}\n"
        context += f"• Average Transaction: ${avg:.2f}\n"
        context += f"• Daily Average: ${(total/days):.2f}\n\n"
        
        # Category breakdown
        if ColumnNames.CATEGORY in expenses_df.columns:
            top_cats = expenses_df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().abs().nlargest(10)
            context += "=== TOP 10 SPENDING CATEGORIES ===\n"
            for i, (cat, amt) in enumerate(top_cats.items(), 1):
                pct = (amt / total) * 100
                count = len(expenses_df[expenses_df[ColumnNames.CATEGORY] == cat])
                context += f"{i}. {cat}: ${amt:,.2f} ({pct:.1f}%) - {count} transactions\n"
            context += "\n"
        
        # Subcategory breakdown (if available)
        if ColumnNames.SUBCATEGORY in expenses_df.columns:
            top_subcats = expenses_df.groupby(ColumnNames.SUBCATEGORY)[ColumnNames.AMOUNT].sum().abs().nlargest(5)
            context += "=== TOP 5 SUBCATEGORIES ===\n"
            for i, (subcat, amt) in enumerate(top_subcats.items(), 1):
                pct = (amt / total) * 100
                context += f"{i}. {subcat}: ${amt:,.2f} ({pct:.1f}%)\n"
            context += "\n"
        
        # Merchant analysis
        if ColumnNames.MERCHANT in expenses_df.columns:
            top_merchants_freq = expenses_df[ColumnNames.MERCHANT].value_counts().head(5)
            context += "=== TOP 5 MERCHANTS (by frequency) ===\n"
            for i, (merchant, count) in enumerate(top_merchants_freq.items(), 1):
                merchant_total = abs(expenses_df[expenses_df[ColumnNames.MERCHANT] == merchant][ColumnNames.AMOUNT].sum())
                context += f"{i}. {merchant}: {count} visits, ${merchant_total:,.2f}\n"
            context += "\n"
            
            # Top merchants by spending
            top_merchants_amt = expenses_df.groupby(ColumnNames.MERCHANT)[ColumnNames.AMOUNT].sum().abs().nlargest(5)
            context += "=== TOP 5 MERCHANTS (by spending) ===\n"
            for i, (merchant, amt) in enumerate(top_merchants_amt.items(), 1):
                pct = (amt / total) * 100
                context += f"{i}. {merchant}: ${amt:,.2f} ({pct:.1f}%)\n"
            context += "\n"
        
        # Account breakdown (if available)
        if ColumnNames.ACCOUNT in expenses_df.columns:
            account_spending = expenses_df.groupby(ColumnNames.ACCOUNT)[ColumnNames.AMOUNT].sum().abs()
            if len(account_spending) > 0:
                context += "=== SPENDING BY ACCOUNT ===\n"
                for account, amt in account_spending.items():
                    pct = (amt / total) * 100
                    context += f"• {account}: ${amt:,.2f} ({pct:.1f}%)\n"
                context += "\n"
        
        # Monthly trend (if available)
        if ColumnNames.MONTH_STR in expenses_df.columns:
            monthly = expenses_df.groupby(ColumnNames.MONTH_STR)[ColumnNames.AMOUNT].sum().abs()
            if len(monthly) > 0:
                context += "=== MONTHLY SPENDING ===\n"
                for month, amt in monthly.tail(6).items():
                    context += f"• {month}: ${amt:,.2f}\n"
                context += "\n"
        elif ColumnNames.MONTH in expenses_df.columns:
            monthly = expenses_df.groupby(ColumnNames.MONTH)[ColumnNames.AMOUNT].sum().abs()
            if len(monthly) > 0:
                context += "=== MONTHLY SPENDING ===\n"
                for month, amt in monthly.tail(6).items():
                    context += f"• Month {month}: ${amt:,.2f}\n"
                context += "\n"
        
        # Include sample transactions if requested
        if include_samples:
            context += "=== SAMPLE TRANSACTIONS (Recent 5) ===\n"
            cols_to_show = [col for col in [ColumnNames.DATE, ColumnNames.MERCHANT, ColumnNames.CATEGORY, 
                                            ColumnNames.SUBCATEGORY, ColumnNames.AMOUNT, ColumnNames.ACCOUNT] 
                           if col in expenses_df.columns]
            sample = expenses_df[cols_to_show].tail(5)
            
            for i, (idx, row) in enumerate(sample.iterrows(), 1):
                context += f"\nTransaction {i}:\n"
                for col in cols_to_show:
                    value = row[col]
                    if isinstance(value, pd.Timestamp):
                        value = value.strftime('%Y-%m-%d')
                    elif col == ColumnNames.AMOUNT:
                        value = f"${abs(value):,.2f}"
                    context += f"  - {col}: {value}\n"
            context += "\n"
    
    # Net Worth section with clear separator
    if networth_df is not None and len(networth_df) > 0:
        context += """
==================================================
💰 NET WORTH & ASSET DATA
==================================================
"""
        context += "=== NET WORTH DATA ===\n"
        
        # Current net worth
        if 'net_worth' in networth_df.columns:
            current = networth_df['net_worth'].iloc[-1 ]
            context += f"• Current Net Worth: ${current:,.2f}\n"
            
            if len(networth_df) > 1:
                previous = networth_df['net_worth'].iloc[-2]
                change = current - previous
                pct = (change / previous) * 100 if previous != 0 else 0
                context += f"• Change from Previous: ${change:+,.2f} ({pct:+.1f}%)\n"
            
            if len(networth_df) >= 3:
                highest = networth_df['net_worth'].max()
                lowest = networth_df['net_worth'].min()
                context += f"• Historical High: ${highest:,.2f}\n"
                context += f"• Historical Low: ${lowest:,.2f}\n"
                context += f"• Total Records: {len(networth_df)}\n"
        
        context += "\n"
        
        # Show all available columns and their latest values
        context += "=== NET WORTH BREAKDOWN (Latest) ===\n"
        latest_row = networth_df.iloc[-1]
        
        # Exclude certain meta columns from display
        exclude_cols = ['date', 'net_worth']
        value_columns = [col for col in networth_df.columns if col not in exclude_cols]
        
        if value_columns:
            for col in value_columns:
                value = latest_row[col]
                if pd.notna(value) and value != 0:
                    # Try to format as currency if it's a number
                    try:
                        if isinstance(value, (int, float)):
                            context += f"• {col}: ${value:,.2f}\n"
                        else:
                            context += f"• {col}: {value}\n"
                    except:
                        context += f"• {col}: {value}\n"
        
        context += "\n"
        
        # Calculate totals by category if there are numeric columns
        numeric_cols = networth_df.select_dtypes(include=['number']).columns
        numeric_cols = [col for col in numeric_cols if col != 'net_worth']
        
        if len(numeric_cols) > 0:
            context += "=== ASSET CATEGORIES (Current Values) ===\n"
            latest_values = {}
            for col in numeric_cols:
                val = latest_row[col]
                if pd.notna(val) and val != 0:
                    latest_values[col] = val
            
            # Sort by value descending
            sorted_assets = sorted(latest_values.items(), key=lambda x: abs(x[1]), reverse=True)
            total_assets = sum(v for v in latest_values.values() if v > 0)
            
            for i, (asset, value) in enumerate(sorted_assets[:10], 1):
                if value > 0:
                    pct = (value / total_assets * 100) if total_assets > 0 else 0
                    context += f"{i}. {asset}: ${value:,.2f} ({pct:.1f}%)\n"
                else:
                    context += f"{i}. {asset}: ${value:,.2f} (Liability)\n"
            context += "\n"
        
        # Show trend for last few periods
        if 'date' in networth_df.columns and 'net_worth' in networth_df.columns:
            context += "=== NET WORTH TREND (Last 6 Records) ===\n"
            trend_data = networth_df[['date', 'net_worth']].tail(6)
            for _, row in trend_data.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
                context += f"• {date_str}: ${row['net_worth']:,.2f}\n"
            context += "\n"
        
        # Include sample networth record if requested
        if include_samples and len(networth_df) > 0:
            context += "=== SAMPLE NET WORTH RECORD (Latest) ===\n"
            latest = networth_df.iloc[-1]
            for col in networth_df.columns:
                value = latest[col]
                if isinstance(value, pd.Timestamp):
                    value = value.strftime('%Y-%m-%d')
                elif isinstance(value, (int, float)):
                    value = f"${value:,.2f}"
                context += f"  - {col}: {value}\n"
            context += "\n"
    
    context += """
==================================================
REMEMBER: 
"""
    if 'expenses' in data_sources and 'networth' in data_sources:
        context += """- You have access to BOTH expense and net worth data
- For EXPENSE/SPENDING questions → Use the EXPENSE SUMMARY section
- For NET WORTH/ASSET questions → Use the NET WORTH DATA section
"""
    elif 'expenses' in data_sources:
        context += "- You ONLY have access to EXPENSE/SPENDING data\n"
    elif 'networth' in data_sources:
        context += "- You ONLY have access to NET WORTH/ASSET data\n"
    
    context += """- Reference previous messages in the conversation when relevant
- Be specific and use actual numbers from the data
==================================================
"""
    return context

# ================== OLLAMA RESPONSE GENERATOR ==================

def generate_ollama_response(model_name, system_context, conversation_history):
    """Generate response using Ollama with full conversation context"""
    try:
        messages = [{"role": "system", "content": system_context}]
        messages.extend(conversation_history)
        
        response = ollama.chat(
            model=model_name,
            messages=messages,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": 4096,
            }
        )
        
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

# ================== MAIN RENDER FUNCTION ==================

def render_chat_assistant(networth_df, expenses_df):
    """Render the chat assistant interface"""
    st.subheader("💬 Financial Chat Assistant")
    st.markdown("💡 **Have a conversation!** Ask follow-up questions and I'll remember our chat history.")
    
    # Initialize session state
    if 'include_samples' not in st.session_state:
        st.session_state.include_samples = False
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'data_sources' not in st.session_state:
        st.session_state.data_sources = ['expenses', 'networth']
    
    # Check if Ollama is running
    try:
        models = ollama.list()
        available_models = [m['model'] for m in models['models']]
    except Exception as e:
        st.error("❌ Ollama is not running!")
        st.info("""
        **Setup Ollama:**
        1. Download from: https://ollama.com/download
        2. Install and run Ollama
        3. Open terminal: `ollama pull llama3.1:8b`
        4. Restart this app
        """)
        return
    
    if not available_models:
        st.warning("⚠️ No models downloaded!")
        st.info("Run: `ollama pull llama3.1:8b`")
        return
    
    if expenses_df is None:
        st.warning("⚠️ Load expense data first")
        return
    
    # ================== SIDEBAR ==================
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("📁 Data Sources")
        
        # Determine what data is available
        has_expenses = expenses_df is not None and len(expenses_df) > 0
        has_networth = networth_df is not None and len(networth_df) > 0
        
        available_sources = []
        if has_expenses:
            available_sources.append("Expenses")
        if has_networth:
            available_sources.append("Net Worth")
        
        if not available_sources:
            st.error("No data available!")
            return
        
        # Data source selection
        data_selection = st.multiselect(
            "Select data to share with AI:",
            available_sources,
            default=available_sources,
            help="Choose which data the AI can access"
        )
        
        # Map selection to internal names
        data_sources_selected = []
        if "Expenses" in data_selection:
            data_sources_selected.append('expenses')
        if "Net Worth" in data_selection:
            data_sources_selected.append('networth')
        
        # Update session state if changed
        if data_sources_selected != st.session_state.data_sources:
            st.session_state.data_sources = data_sources_selected
            if 'financial_context' in st.session_state:
                del st.session_state.financial_context
            st.info("✅ Data access updated!")
        
        if not data_sources_selected:
            st.warning("⚠️ Select at least one data source")
            return
        
        st.divider()
        st.subheader("🤖 Model Settings")
        
        selected_model = st.selectbox("Select Model", available_models, index=0)
        
        with st.expander("⚙️ Advanced"):
            # This checkbox directly updates session state
            include_samples = st.checkbox(
                "Include sample transactions", 
                value=st.session_state.include_samples,
                key="samples_checkbox",
                help="Include 5 recent transactions in context"
            )
            
            # Update session state if changed
            if include_samples != st.session_state.include_samples:
                st.session_state.include_samples = include_samples
                # Clear cached context to regenerate
                if 'financial_context' in st.session_state:
                    del st.session_state.financial_context
                st.info("✅ Context will refresh on next message")
            
            # Debug option to view context
            if st.checkbox("🔍 Debug: Show context sent to AI", value=False):
                if 'financial_context' in st.session_state:
                    with st.expander("View AI Context"):
                        st.text(st.session_state.financial_context)
                else:
                    st.caption("Send a message to generate context")
        
        st.divider()
        st.subheader("📊 Data Overview")
        
        if expenses_df is not None:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Transactions", f"{len(expenses_df):,}")
            with col2:
                total = abs(expenses_df[ColumnNames.AMOUNT].sum())
                st.metric("Total Spend", f"${total:,.0f}")
            
            if 'expenses' in st.session_state.data_sources:
                st.caption("✅ Expense data - AI has access")
            else:
                st.caption("🔒 Expense data - AI blocked")
        else:
            st.caption("❌ No expense data")
        
        if networth_df is not None and len(networth_df) > 0:
            # Calculate current net worth (group by latest date and sum amounts)
            if ColumnNames.MONTH in networth_df.columns and ColumnNames.AMOUNT in networth_df.columns:
                networth_df[ColumnNames.MONTH] = pd.to_datetime(networth_df[ColumnNames.MONTH])
                latest_date = networth_df[ColumnNames.MONTH].max()
                latest_data = networth_df[networth_df[ColumnNames.MONTH] == latest_date]
                
                current_net_worth = latest_data[ColumnNames.AMOUNT].sum()
                total_assets = latest_data[latest_data[ColumnNames.AMOUNT] > 0][ColumnNames.AMOUNT].sum()
                total_liabilities = abs(latest_data[latest_data[ColumnNames.AMOUNT] < 0][ColumnNames.AMOUNT].sum())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Net Worth", f"${current_net_worth:,.0f}")
                with col2:
                    st.metric("Assets", f"${total_assets:,.0f}")
                    st.caption(f"Liabilities: ${total_liabilities:,.0f}")
                
                num_dates = networth_df[ColumnNames.MONTH].nunique()
                num_accounts = len(latest_data)
                
                if 'networth' in st.session_state.data_sources:
                    st.caption(f"✅ Net worth data - AI has access ({num_dates} snapshots)")
                else:
                    st.caption(f"🔒 Net worth data - AI blocked ({num_dates} snapshots)")
                st.caption(f"📁 Accounts tracked: {num_accounts}")
            else:
                st.caption("⚠️ Net worth data structure issue")
        else:
            st.caption("❌ No net worth data")
        
        st.divider()
        st.subheader("💡 Example Questions")
        
        st.caption("**Try a conversation:**")
        st.markdown("""
        1️⃣ Ask a question  
        2️⃣ "Tell me more about that"  
        3️⃣ "How can I improve?"
        """)
        
        # Show expense examples if expenses are selected
        if 'expenses' in st.session_state.data_sources:
            st.caption("**💳 Expense Questions:**")
            
            expense_examples = [
                "Top 10 spending categories?",
                "How much on groceries?",
                "Which merchant most frequent?",
                "Monthly spending trends?",
            ]
            
            for i, q in enumerate(expense_examples):
                if st.button(q, key=f"exp_{i}", use_container_width=True):
                    st.session_state.selected_q = q
        
        # Show networth examples if networth is selected
        if 'networth' in st.session_state.data_sources:
            st.caption("**💰 Net Worth Questions:**")
            
            networth_examples = [
                "What's my current net worth?",
                "How has my net worth changed?",
                "Break down by account type",
                "Which accounts are largest?",
                "Show net worth trend",
                "What's in my Brokerage accounts?",
            ]
            
            for i, q in enumerate(networth_examples):
                if st.button(q, key=f"nw_{i}", use_container_width=True):
                    st.session_state.selected_q = q
        
        # Combined questions if both are selected
        if 'expenses' in st.session_state.data_sources and 'networth' in st.session_state.data_sources:
            st.caption("**🔄 Combined Analysis:**")
            
            combined_examples = [
                "How does my spending compare to net worth growth?",
                "Am I saving enough based on my expenses?",
                "What's my savings rate?",
            ]
            
            for i, q in enumerate(combined_examples):
                if st.button(q, key=f"comb_{i}", use_container_width=True):
                    st.session_state.selected_q = q
        
        st.divider()
        
        if st.session_state.chat_messages:
            st.caption(f"💬 Messages: {len(st.session_state.chat_messages)}")
            
            if st.button("🔄 Refresh Data", use_container_width=True):
                if 'financial_context' in st.session_state:
                    del st.session_state.financial_context
                st.success("✅ Will refresh!")
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            if 'financial_context' in st.session_state:
                del st.session_state.financial_context
            # Don't reset data_sources - keep user's selection
            st.rerun()
    
    # ================== CHAT INTERFACE ==================
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Get input
    prompt = None
    if "selected_q" in st.session_state:
        prompt = st.session_state.selected_q
        del st.session_state.selected_q
    else:
        prompt = st.chat_input("Ask about your finances...")
    
    # Process input
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Generate context if not cached
                    if 'financial_context' not in st.session_state:
                        st.session_state.financial_context = create_financial_context(
                            expenses_df, 
                            networth_df, 
                            st.session_state.include_samples,
                            st.session_state.data_sources
                        )
                    
                    # Generate response
                    response = generate_ollama_response(
                        selected_model,
                        st.session_state.financial_context,
                        st.session_state.chat_messages
                    )
                    
                    st.markdown(response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                
                except Exception as e:
                    error = f"❌ Error: {str(e)}"
                    st.error(error)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error})
