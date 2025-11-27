import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Equipment Manager",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling and BLACK TEXT for metrics
st.markdown("""
    <style>
    /* Style for Metrics container */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #d6d6d6;
    }
    
    /* Force Metric Label (Title) to Black */
    label[data-testid="stMetricLabel"] {
        color: #000000 !important;
    }
    
    /* Force Metric Value (Number) to Black */
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
    }

    .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE FUNCTIONS ---
def get_database_connection():
    return sqlite3.connect('Test_equipment_database.db')

def fetch_types(conn):
    """Fetch distinct Types from the database."""
    try:
        query = "SELECT DISTINCT Type FROM Equipment_List"
        return pd.read_sql_query(query, conn)['Type'].tolist()
    except Exception:
        return []

def fetch_equipment_data(conn, availability='All', equipment_type='ALL'):
    """Fetch equipment based on availability and type."""
    query_conditions = []
    params = []

    if availability != 'All':
        query_conditions.append('Loan_History.Availability = ?')
        params.append(availability)

    if equipment_type != 'ALL':
        query_conditions.append("Equipment_List.Type = ?")
        params.append(equipment_type)

    availability_condition = ' AND '.join(query_conditions) if query_conditions else '1=1'

    query = f"""
    SELECT 
        Equipment_List.Equipment_ID AS ID,
        Equipment_List.Type,
        Equipment_List.Name,
        Equipment_List.Brand,
        Equipment_List.Qty,
        Loan_History.Availability,
        Loan_History.Loan_From AS Loan_Start
    FROM Equipment_List
    JOIN Loan_History ON Equipment_List.Equipment_ID = Loan_History.Equipment_ID
    WHERE {availability_condition}
    """
    
    return pd.read_sql_query(query, conn, params=params)

# --- 3. SESSION STATE SETUP ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.title("🛠️ Lab Manager")

# Login Logic
if not st.session_state.authenticated:
    with st.sidebar.expander("🔐 Staff Login", expanded=True):
        with st.form("login_form"):
            name = st.selectbox("Select Name", ["Tobby", "Rex"], index=None, placeholder="Choose user...")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if name and password == "0000":
                    st.session_state.authenticated = True
                    st.toast(f"Welcome back, {name}!", icon="👋")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    
    # If not logged in, only show View Equipment
    page_options = ["View Equipment"]
else:
    st.sidebar.success("Logged in as Staff")
    if st.sidebar.button("Logout", icon="🔒"):
        st.session_state.authenticated = False
        st.rerun()
    # Full navigation (Overview removed as requested)
    page_options = ["View Equipment", "Loan & Return"]

# Use radio button for navigation
selected_page = st.sidebar.radio("Navigation", page_options)


# --- 5. MAIN PAGE LOGIC ---

# === PAGE: VIEW EQUIPMENT ===
if selected_page == "View Equipment":
    st.title("🔎 Equipment Inventory")
    
    with get_database_connection() as conn:
        types = fetch_types(conn)
        
        # Dashboard Metrics (Quick Stats)
        try:
            df_all = fetch_equipment_data(conn)
            total_items = len(df_all)
            available_items = len(df_all[df_all['Availability'] == 'Yes'])
            loaned_items = len(df_all[df_all['Availability'] == 'No'])

            c1, c2, c3 = st.columns(3)
            # Text color forced to black via CSS at top of script
            c1.metric("Total Assets", total_items)
            c2.metric("Available", available_items)
            c3.metric("Loaned Out", loaned_items)
        except Exception:
            st.warning("Could not load metrics. Database might be empty.")

        st.divider()

        # Filters
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_type = st.selectbox('Filter by Type', ['ALL'] + types)
        with col2:
            selected_availability = st.selectbox('Filter by Status', ["All", "Available Only", "Loaned Out"])
        
        avail_map = {"All": "All", "Available Only": "Yes", "Loaned Out": "No"}
        
        try:
            filtered_data = fetch_equipment_data(conn, avail_map[selected_availability], selected_type)
            
            if filtered_data.empty:
                st.info("No equipment found matching these criteria.")
            else:
                st.dataframe(
                    filtered_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Availability": st.column_config.TextColumn(
                            "Status",
                            validate="^(Yes|No)$"
                        ),
                        "Loan_Start": st.column_config.DateColumn(
                            "Loaned Since",
                            format="YYYY-MM-DD"
                        )
                    }
                )
        except Exception as e:
            st.error(f"Database Error: {e}")

    # Chatbot Component (Moved here)
    st.divider()
    with st.expander("💬 Open Support Assistant", expanded=False):
        chatbot_code = """
        <div id="chatbot-container"></div>
        <script src="https://cdn.botpress.cloud/webchat/v3.3/inject.js" defer></script>
        <script src="https://files.bpcontent.cloud/2025/11/27/06/20251127065604-HBKZN89E.js" defer></script>
        """
        components.html(chatbot_code, height=500)


# === PAGE: LOAN & RETURN ===
elif selected_page == "Loan & Return":
    st.title("📑 Equipment Loan & Return")
    
    with get_database_connection() as conn:
        types = fetch_types(conn)
        
        tab_loan, tab_return = st.tabs(["📤 Loan Out", "📥 Return Item"])

        # --- LOAN TAB ---
        with tab_loan:
            st.subheader("Process New Loan")
            
            col_filter, col_date = st.columns(2)
            with col_filter:
                loan_type_filter = st.selectbox("Filter Available Items by Type", ['ALL'] + types, key="loan_type")
            with col_date:
                loan_date = st.date_input("Loan Start Date", value=date.today())

            available_data = fetch_equipment_data(conn, 'Yes', loan_type_filter)

            if not available_data.empty:
                with st.form("loan_form"):
                    st.write("Select Items to Loan:")
                    
                    # Create a scrollable container for checkboxes
                    selected_ids = []
                    with st.container(height=300, border=True):
                        # Iterate through data to create checkboxes
                        for index, row in available_data.iterrows():
                            # Use unique keys for each checkbox
                            is_checked = st.checkbox(
                                f"{row['Name']} (ID: {row['ID']})", 
                                key=f"loan_chk_{row['ID']}"
                            )
                            if is_checked:
                                selected_ids.append(row['ID'])
                    
                    submitted_loan = st.form_submit_button("Confirm Loan ✅", type="primary")

                    if submitted_loan:
                        if selected_ids:
                            try:
                                for equipment_id in selected_ids:
                                    conn.execute(
                                        "UPDATE Loan_History SET Availability = 'No', Loan_From = ? WHERE Equipment_ID = ?", 
                                        (loan_date, equipment_id)
                                    )
                                conn.commit()
                                st.toast(f"Successfully loaned {len(selected_ids)} item(s)!", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Please check at least one item.")
            else:
                st.info("No items currently available for this type.")

        # --- RETURN TAB ---
        with tab_return:
            st.subheader("Process Return")
            
            return_type_filter = st.selectbox("Filter Loaned Items by Type", ['ALL'] + types, key="return_type")
            unavailable_data = fetch_equipment_data(conn, 'No', return_type_filter)

            if not unavailable_data.empty:
                with st.form("return_form"):
                    st.write("Select Items to Return:")
                    
                    selected_return_ids = []
                    # Create a scrollable container for checkboxes
                    with st.container(height=300, border=True):
                        for index, row in unavailable_data.iterrows():
                            # Use unique keys for each checkbox
                            is_checked = st.checkbox(
                                f"{row['Name']} (ID: {row['ID']})", 
                                key=f"ret_chk_{row['ID']}"
                            )
                            if is_checked:
                                selected_return_ids.append(row['ID'])

                    submitted_return = st.form_submit_button("Confirm Return 📥", type="primary")

                    if submitted_return:
                        if selected_return_ids:
                            try:
                                for equipment_id in selected_return_ids:
                                    conn.execute(
                                        "UPDATE Loan_History SET Availability = 'Yes', Loan_From = NULL WHERE Equipment_ID = ?",
                                        (equipment_id,)
                                    )
                                conn.commit()
                                st.toast(f"Successfully returned {len(selected_return_ids)} item(s)!", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Please check at least one item.")
            else:
                st.info("No items currently loaned out for this type.")
