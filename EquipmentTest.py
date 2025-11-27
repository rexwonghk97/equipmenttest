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

# Custom CSS for better styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
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

    # Determine availability filter
    if availability != 'All':
        query_conditions.append('Loan_History.Availability = ?')
        params.append(availability)

    # Determine type filter
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
    
    # Restrict navigation if not logged in
    page_options = ["Overview", "View Equipment"]
else:
    st.sidebar.success("Logged in as Staff")
    if st.sidebar.button("Logout", icon="🔒"):
        st.session_state.authenticated = False
        st.rerun()
    # Full navigation
    page_options = ["Overview", "View Equipment", "Loan & Return"]

# Use radio button for smoother navigation state
selected_page = st.sidebar.radio("Navigation", page_options)


# --- 5. MAIN PAGE LOGIC ---

# === PAGE: OVERVIEW ===
if selected_page == "Overview":
    st.title("🖥️ System Overview")
    st.info("Welcome to the Equipment Management System.")
    
    # Embed Chatbot
    st.subheader("Support Assistant")
    chatbot_code = """
    <div id="chatbot-container"></div>
    <script src="https://cdn.botpress.cloud/webchat/v3.3/inject.js" defer></script>
    <script src="https://files.bpcontent.cloud/2025/11/27/06/20251127065604-HBKZN89E.js" defer></script>
    """
    components.html(chatbot_code, height=600)

# === PAGE: VIEW EQUIPMENT ===
elif selected_page == "View Equipment":
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
            c1.metric("Total Assets", total_items)
            c2.metric("Available", available_items, delta_color="normal")
            c3.metric("Loaned Out", loaned_items, delta_color="inverse")
        except Exception:
            st.warning("Could not load metrics. Database might be empty.")

        st.divider()

        # Filters using columns for better layout
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            selected_type = st.selectbox('Filter by Type', ['ALL'] + types)
        with col2:
            selected_availability = st.selectbox('Filter by Status', ["All", "Available Only", "Loaned Out"])
        
        # Map UI selection to DB values
        avail_map = {"All": "All", "Available Only": "Yes", "Loaned Out": "No"}
        
        # Fetch Data
        try:
            filtered_data = fetch_equipment_data(conn, avail_map[selected_availability], selected_type)
            
            if filtered_data.empty:
                st.info("No equipment found matching these criteria.")
            else:
                # Use st.dataframe for an interactive table
                st.dataframe(
                    filtered_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Availability": st.column_config.TextColumn(
                            "Status",
                            help="Current status of the item",
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
                # UX Improvement: Date Picker
                loan_date = st.date_input("Loan Start Date", value=date.today())

            available_data = fetch_equipment_data(conn, 'Yes', loan_type_filter)

            if not available_data.empty:
                with st.form("loan_form"):
                    selected_ids = st.multiselect(
                        "Select Items to Loan",
                        options=available_data['ID'],
                        format_func=lambda x: f"{available_data.loc[available_data['ID'] == x, 'Name'].values[0]} (ID: {x})"
                    )
                    
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
                                st.rerun() # Refresh page immediately
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Please select at least one item.")
            else:
                st.info("No items currently available for this type.")

        # --- RETURN TAB ---
        with tab_return:
            st.subheader("Process Return")
            
            return_type_filter = st.selectbox("Filter Loaned Items by Type", ['ALL'] + types, key="return_type")
            unavailable_data = fetch_equipment_data(conn, 'No', return_type_filter)

            if not unavailable_data.empty:
                with st.form("return_form"):
                    selected_return_ids = st.multiselect(
                        "Select Items to Return",
                        options=unavailable_data['ID'],
                        format_func=lambda x: f"{unavailable_data.loc[unavailable_data['ID'] == x, 'Name'].values[0]} (ID: {x})"
                    )

                    submitted_return = st.form_submit_button("Confirm Return 📥", type="
