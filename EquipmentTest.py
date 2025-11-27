import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
import altair as alt  # Built-in to Streamlit
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
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .metric-info {
        text-align: left;
    }
    .metric-title {
        color: #6c757d;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-value {
        color: #212529;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-icon {
        font-size: 2rem;
        padding: 12px;
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
def display_metric_card_horizontal(title, value, icon, color_bg):
    st.markdown(f"""
    <div class="metric-card-container">
        <div class="metric-info">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        <div class="metric-icon" style="background-color: {color_bg};">
            {icon}
        </div>
    </div>
    """, unsafe_allow_html=True)


# --- 6. MAIN PAGE LOGIC ---

# === PAGE: VIEW EQUIPMENT ===
if selected_page == "View Equipment":
    st.title("🔎 Equipment Inventory")
    
    with get_database_connection() as conn:
        types = fetch_types(conn)
        
        # --- DASHBOARD SECTION ---
        try:
            df_all = fetch_equipment_data(conn)
            total = len(df_all)
            avail = len(df_all[df_all['Availability'] == 'Yes'])
            loaned = len(df_all[df_all['Availability'] == 'No'])
            
            chart_col, metrics_col = st.columns([1.5, 1])
            
            with chart_col:
                # Prepare data
                chart_data = pd.DataFrame({
                    "Status": ["Available", "Loaned Out"],
                    "Count": [avail, loaned]
                })

                # Create Altair Donut Chart
                base = alt.Chart(chart_data).encode(
                    theta=alt.Theta("Count", stack=True)
                )
                
                pie = base.mark_arc(innerRadius=60).encode(
                    color=alt.Color("Status", scale=alt.Scale(domain=["Available", "Loaned Out"], range=["#66bb6a", "#ffa726"])),
                    order=alt.Order("Count", sort="descending"),
                    tooltip=["Status", "Count"]
                )
                
                text = base.mark_text(radius=0).encode(
                    text=alt.value(f"{total}"),
                    size=alt.value(30),
                    color=alt.value("#333333") 
                )
                
                text_label = base.mark_text(radius=0, dy=20).encode(
                    text=alt.value("Assets"),
                    size=alt.value(12),
                    color=alt.value("#666666")
                )

                st.altair_chart(pie + text + text_label, use_container_width=True)

            with metrics_col:
                st.w
