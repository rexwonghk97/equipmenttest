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

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    /* MAIN CONTAINER PADDING */
    .block-container {
        padding-top: 1.5rem;
    }

    /* CUSTOM METRIC CARDS */
    .metric-card-container {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    .metric-title {
        color: #6c757d;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #212529;
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-icon {
        font-size: 1.5rem;
        margin-bottom: 10px;
        display: inline-block;
        padding: 10px;
        border-radius: 50%;
    }
    
    /* ROW ITEM STYLING IN LOAN/RETURN */
    .item-row {
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATABASE FUNCTIONS ---
def get_database_connection():
    return sqlite3.connect('Test_equipment_database.db')

def fetch_types(conn):
    try:
        query = "SELECT DISTINCT Type FROM Equipment_List"
        return pd.read_sql_query(query, conn)['Type'].tolist()
    except Exception:
        return []

def fetch_equipment_data(conn, availability='All', equipment_type='ALL'):
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
        Equipment_List.item_created AS Created_Date,
        Loan_History.Availability,
        Loan_History.Loan_From AS Loan_Start
    FROM Equipment_List
    JOIN Loan_History ON Equipment_List.Equipment_ID = Loan_History.Equipment_ID
    WHERE {availability_condition}
    """
    return pd.read_sql_query(query, conn, params=params)

# --- 4. SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 5. SIDEBAR NAVIGATION ---
st.sidebar.title("🛠️ Lab Manager")

if not st.session_state.authenticated:
    with st.sidebar.expander("🔐 Staff Login", expanded=True):
        with st.form("login_form"):
            name = st.selectbox("Select Name", ["Tobby", "Rex"], index=None, placeholder="Choose user...")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted and name and password == "0000":
                st.session_state.authenticated = True
                st.toast(f"Welcome back, {name}!", icon="👋")
                st.rerun()
            elif submitted:
                st.error("Invalid credentials.")
    page_options = ["View Equipment"]
else:
    st.sidebar.success("Logged in as Staff")
    if st.sidebar.button("Logout", icon="🔒"):
        st.session_state.authenticated = False
        st.rerun()
    page_options = ["View Equipment", "Loan & Return"]

selected_page = st.sidebar.radio("Navigation", page_options)


# --- HELPER FUNCTION FOR METRIC CARDS ---
def display_metric_card(title, value, icon, color_bg):
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-icon" style="background-color: {color_bg};">
            {icon}
        </div>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# --- 6. MAIN PAGE LOGIC ---

# === PAGE: VIEW EQUIPMENT ===
if selected_page == "View Equipment":
    st.title("🔎 Equipment Inventory")
    
    with get_database_connection() as conn:
        types = fetch_types(conn)
        
        # 1. Dashboard Metrics
        try:
            df_all = fetch_equipment_data(conn)
            total = len(df_all)
            avail = len(df_all[df_all['Availability'] == 'Yes'])
            loaned = len(df_all[df_all['Availability'] == 'No'])

            c1, c2, c3 = st.columns(3)
            with c1:
                display_metric_card("Total Assets", total, "📦", "#e3f2fd")
            with c2:
                display_metric_card("Available", avail, "✅", "#e8f5e9")
            with c3:
                display_metric_card("Loaned Out", loaned, "⏳", "#fff3e0")

        except Exception:
            st.warning("Could not load metrics. Database might be empty.")

        st.write("") 
        
        # 2. Filters & Dataframe
        with st.container(border=True):
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
                            "Availability": st.column_config.TextColumn("Status", width="medium", validate="^(Yes|No)$"),
                            "Loan_Start": st.column_config.DateColumn("Loaned Since", format="YYYY-MM-DD"),
                            "ID": st.column_config.TextColumn("ID", width="small"),
                            "Qty": st.column_config.NumberColumn("Qty", width="small")
                        }
                    )
            except Exception as e:
                st.error(f"Database Error: {e}")

    # 3. Floating Chatbot (No Expander)
    # We use a custom HTML block with fixed positioning to "Float" the chatbot 
    # at the bottom left of the screen.
    chatbot_code = """
    <div id="chatbot-container"></div>
    <!-- Load Botpress Scripts -->
    <script src="https://cdn.botpress.cloud/webchat/v3.4/inject.js"></script>
    <script src="https://files.bpcontent.cloud/2025/11/27/17/20251127174335-663UOJ00.js" defer></script>
    
    <!-- Custom CSS to Force Left Positioning inside the iframe -->
    <style>
        /* This moves the chatbot bubble/window to the left side */
        .bp-widget-widget { left: 200px !important; right: auto !important; }
        .bp-widget-side { left: 200px !important; right: auto !important; }
    </style>
    """
    
    # We render this in an HTML component. 
    # Note: Streamlit puts this in an iframe at the bottom of the page flow.
    # To use it, the user scrolls to the bottom.
    components.html(chatbot_code, height=700)


# === PAGE: LOAN & RETURN ===
elif selected_page == "Loan & Return":
    st.title("📑 Equipment Loan & Return")
    
    with get_database_connection() as conn:
        types = fetch_types(conn)
        tab_loan, tab_return = st.tabs(["📤 Loan Out", "📥 Return Item"])

        # --- LOAN TAB ---
        with tab_loan:
            st.subheader("Process New Loan")
            c_fil, c_date = st.columns([1, 1])
            with c_fil:
                loan_type_filter = st.selectbox("Filter by Type", ['ALL'] + types, key="loan_type")
            with c_date:
                loan_date = st.date_input("Loan Start Date", value=date.today())

            available_data = fetch_equipment_data(conn, 'Yes', loan_type_filter)

            if not available_data.empty:
                with st.form("loan_form"):
                    st.markdown("### Select Items to Loan")
                    st.caption("Check the box on the left to select an item.")
                    
                    # Headers
                    h1, h2, h3, h4 = st.columns([0.5, 2.5, 2, 2])
                    h1.markdown("**Select**")
                    h2.markdown("**Equipment**")
                    h3.markdown("**Details**")
                    h4.markdown("**Status**")
                    st.divider()

                    selected_ids = []
                    with st.container(height=400):
                        for index, row in available_data.iterrows():
                            c1, c2, c3, c4 = st.columns([0.5, 2.5, 2, 2])
                            with c1:
                                is_checked = st.checkbox("", key=f"loan_chk_{row['ID']}")
                                if is_checked: selected_ids.append(row['ID'])
                            with c2:
                                st.markdown(f"**{row['Name']}**")
                                st.caption(f"ID: {row['ID']}")
                            with c3:
                                st.text(f"Brand: {row['Brand']}")
                                st.text(f"Type:  {row['Type']}")
                            with c4:
                                st.markdown(f"Qty: **{row['Qty']}**")
                                st.caption(f"Created: {row['Created_Date']}")
                            st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

                    st.write("")
                    submitted_loan = st.form_submit_button("Confirm Loan ✅", type="primary")

                    if submitted_loan:
                        if selected_ids:
                            try:
                                for equipment_id in selected_ids:
                                    conn.execute("UPDATE Loan_History SET Availability = 'No', Loan_From = ? WHERE Equipment_ID = ?", (loan_date, equipment_id))
                                conn.commit()
                                st.toast(f"Success! Loaned {len(selected_ids)} items.", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Select at least one item.")
            else:
                st.info("No items available.")

        # --- RETURN TAB ---
        with tab_return:
            st.subheader("Process Return")
            return_type_filter = st.selectbox("Filter by Type", ['ALL'] + types, key="return_type")
            unavailable_data = fetch_equipment_data(conn, 'No', return_type_filter)

            if not unavailable_data.empty:
                with st.form("return_form"):
                    st.markdown("### Select Items to Return")
                    h1, h2, h3, h4 = st.columns([0.5, 2.5, 2, 2])
                    h1.markdown("**Select**")
                    h2.markdown("**Equipment**")
                    h3.markdown("**Details**")
                    h4.markdown("**Loan Info**")
                    st.divider()

                    selected_return_ids = []
                    with st.container(height=400):
                        for index, row in unavailable_data.iterrows():
                            c1, c2, c3, c4 = st.columns([0.5, 2.5, 2, 2])
                            with c1:
                                is_checked = st.checkbox("", key=f"ret_chk_{row['ID']}")
                                if is_checked: selected_return_ids.append(row['ID'])
                            with c2:
                                st.markdown(f"**{row['Name']}**")
                                st.caption(f"ID: {row['ID']}")
                            with c3:
                                st.text(f"Brand: {row['Brand']}")
                                st.text(f"Type:  {row['Type']}")
                            with c4:
                                st.markdown(f"📅 **{row['Loan_Start']}**")
                                st.caption("Status: On Loan")
                            st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

                    st.write("")
                    submitted_return = st.form_submit_button("Confirm Return 📥", type="primary")

                    if submitted_return:
                        if selected_return_ids:
                            try:
                                for equipment_id in selected_return_ids:
                                    conn.execute("UPDATE Loan_History SET Availability = 'Yes', Loan_From = NULL WHERE Equipment_ID = ?", (equipment_id,))
                                conn.commit()
                                st.toast(f"Success! Returned {len(selected_return_ids)} items.", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Select at least one item.")
            else:
                st.info("No items loaned out.")
