"""UI components for filters."""

import streamlit as st


def render_header_filters(data):
    """Render account type and category segmented controls.
    
    Args:
        data: Full dataset
        
    Returns:
        Tuple of (selected_account_types, selected_categories)
    """
    acct_types = sorted(data['Account Type'].unique())
    selected_account_types = st.segmented_control(
        "Account Type", 
        options=acct_types, 
        selection_mode="multi", 
        default=acct_types
    )
    
    categories = data[data['Account Type'].isin(selected_account_types)]['Category'].unique() if selected_account_types else data['Category'].unique()
    selected_categories = st.segmented_control(
        "Category", 
        options=categories, 
        selection_mode="multi", 
        default=categories
    )
    
    return selected_account_types, selected_categories


def render_sidebar_filters(data, accounts, account_info):
    """Render sidebar with account selection and search.
    
    Args:
        data: Full dataset
        accounts: List of available accounts
        account_info: Dictionary with account details
        
    Returns:
        List of selected accounts
    """
    st.sidebar.markdown("### Account Filter")
    
    # Initialize session state
    if 'selected_accounts' not in st.session_state:
        st.session_state.selected_accounts = accounts.copy()
    
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    
    # Search box
    search = st.sidebar.text_input("Search accounts", "", placeholder="Type to filter...")
    
    # Filter accounts based on search
    filtered_accounts = [a for a in accounts if search.lower() in a.lower()] if search else accounts
    
    # Group accounts by type
    grouped_accounts = {}
    for acc in filtered_accounts:
        acct_type = account_info.get(acc, {}).get('type', 'Unknown')
        if acct_type not in grouped_accounts:
            grouped_accounts[acct_type] = []
        grouped_accounts[acct_type].append(acc)
    
    # Initialize expander states
    for acct_type in grouped_accounts.keys():
        if acct_type not in st.session_state.expander_states:
            st.session_state.expander_states[acct_type] = True
    
    # Check if most expanders are expanded
    expanded_count = sum(1 for state in st.session_state.expander_states.values() if state)
    total_count = len(st.session_state.expander_states)
    mostly_expanded = expanded_count > total_count / 2 if total_count > 0 else True
    
    # Quick actions
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("Select All", use_container_width=True):
            st.session_state.selected_accounts = accounts.copy()
    with col2:
        if st.button("Clear All", use_container_width=True):
            st.session_state.selected_accounts = []
    with col3:
        toggle_label = "Collapse" if mostly_expanded else "Expand"
        if st.button(toggle_label, use_container_width=True):
            new_state = not mostly_expanded
            for acct_type in grouped_accounts.keys():
                st.session_state.expander_states[acct_type] = new_state
    
    # Grouped display
    for acct_type in sorted(grouped_accounts.keys()):
        accts = grouped_accounts[acct_type]
        is_expanded = st.session_state.expander_states.get(acct_type, True)
        
        with st.sidebar.expander(f"{acct_type} ({len(accts)})", expanded=is_expanded):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Select All", use_container_width=True, key=f"all_{acct_type}"):
                    current = set(st.session_state.selected_accounts)
                    current.update(accts)
                    st.session_state.selected_accounts = list(current)
            with col2:
                if st.button("Clear All", use_container_width=True, key=f"none_{acct_type}"):
                    st.session_state.selected_accounts = [a for a in st.session_state.selected_accounts if a not in accts]
            
            for acc in accts:
                info = account_info.get(acc, {})
                label = f"{acc} ({info.get('trend', '→')} ${info.get('value', 0):,.0f})" if info else acc
                is_selected = acc in st.session_state.selected_accounts
                
                if st.checkbox(label, value=is_selected, key=f"check_{acc}"):
                    if acc not in st.session_state.selected_accounts:
                        st.session_state.selected_accounts.append(acc)
                else:
                    if acc in st.session_state.selected_accounts:
                        st.session_state.selected_accounts.remove(acc)
    
    # Summary statistics
    st.sidebar.divider()
    count = len(st.session_state.selected_accounts)
    total = len(accounts)
    
    if count > 0:
        selected_value = sum(account_info.get(a, {}).get('value', 0) for a in st.session_state.selected_accounts)
        total_value = sum(account_info.get(a, {}).get('value', 0) for a in accounts)
        
        if count == total:
            st.sidebar.success(f"{count} of {total} selected")
        else:
            st.sidebar.info(f"{count} of {total} selected")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Selected", f"${selected_value:,.0f}")
        with col2:
            pct = (selected_value / total_value * 100) if total_value != 0 else 0
            st.metric("% of Total", f"{pct:.1f}%")
    else:
        st.sidebar.error("No accounts selected")
    
    if search:
        st.sidebar.caption(f"{len(filtered_accounts)} matches")
    
    return st.session_state.selected_accounts
