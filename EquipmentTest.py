import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components

# Set up the database connection
def get_database_connection():
    return sqlite3.connect('Test_equipment_database.db')

def fetch_types(conn):
    """Fetch distinct Types from the database."""
    query = "SELECT DISTINCT Type FROM Equipment_List"
    return pd.read_sql_query(query, conn)['Type'].tolist()

def fetch_equipment_data(conn, availability, equipment_type='ALL'):
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

    # Create the SQL query with conditions
    availability_condition = ' AND '.join(query_conditions) if query_conditions else '1=1'  # If no conditions, return everything

    query = f"""
    SELECT 
        Equipment_List.Equipment_ID AS EquipmentList_ID,
        Equipment_List.Type AS Equipment_Type,
        Equipment_List.Name AS Equipment_Name,
        Equipment_List.Brand AS Equipment_Brand,
        Equipment_List.Qty AS Equipment_Qty,
        Equipment_List.item_created AS Equipment_Created,
        Loan_History.Availability AS Equipment_Availability,
        Loan_History.Loan_From AS Loan_Start_Date
    FROM Equipment_List
    JOIN Loan_History ON Equipment_List.Equipment_ID = Loan_History.Equipment_ID
    WHERE {availability_condition}
    """
    
    return pd.read_sql_query(query, conn, params=params)

# Set a session state variable to track which section is active
if 'active_page' not in st.session_state:
    st.session_state.active_page = "Overview"  # Default to Overview

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False  # Track authentication status

# Track if the login expander is open
if 'login_expander_open' not in st.session_state:
    st.session_state.login_expander_open = True  # Keep it true initially for the first time

st.markdown(
    """
    <style>
    .stButton > button {
        min-width: 200px;  /* Minimum width */
        width: 200px;      /* Fixed width */
        height: 40px;      /* Optional: Set standard height */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar buttons for navigation
overview_button = st.sidebar.button("🖥️ Overview")
query_function_button = st.sidebar.button("🔎 View Equipment")
loadreturn_button = st.sidebar.button("📑 Loan & Return")

# Authentication section
if not st.session_state.authenticated:
    with st.sidebar.expander("Login (Staff Only)", expanded=st.session_state.login_expander_open):
        name = st.selectbox("Select Your Name", ["Select...", "Tobby", "Rex"], index=0)
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if name != "Select..." and password == "0000":
                st.session_state.authenticated = True
                st.session_state.login_expander_open = False  # Close expander after successful login
                st.session_state.active_page = "Equipment Loan & Return"  # Navigate after login
            else:
                st.error("Invalid Password!")

# Check button clicks and handle navigation
if overview_button:
    st.session_state.active_page = "Overview"
elif query_function_button:
    st.session_state.active_page = "View Equipment"
elif loadreturn_button and st.session_state.authenticated:
    st.session_state.active_page = "Equipment Loan & Return"

# Conditional rendering based on the active page
if st.session_state.active_page == "Overview":
    tab1 = st.tabs(["Information"])[0]  # Only tab1 is created
    with tab1:
        st.title('Overview:')
        st.subheader('This is a test page for viewing equipment')
       
        chatbot_code = """
        <div id="chatbot-container"></div>
        <script src="https://cdn.botpress.cloud/webchat/v3.3/inject.js" defer></script>
        <script src="https://files.bpcontent.cloud/2025/11/27/06/20251127065604-HBKZN89E.js" defer></script>
        """

        # Render the chatbot code
        components.html(chatbot_code, height=600)  # Adjust height as necessary

elif st.session_state.active_page == "View Equipment":
    with get_database_connection() as conn:
        types = fetch_types(conn)

        tab3, tab4 = st.tabs(["Find All Equipment", "Find Available Equipment"])

        with tab3:
            st.write("Find All Equipment 🔎")
            try:
                query = """
                SELECT 
                    Equipment_List.Equipment_ID AS EquipmentList_ID,
                    Equipment_List.Type AS Equipment_Type,
                    Equipment_List.Name AS Equipment_Name,
                    Equipment_List.Brand AS Equipment_Brand,
                    Equipment_List.Qty AS Equipment_Qty,
                    Equipment_List.item_created AS Equipment_Created,
                    Loan_History.Availability AS Equipment_Availability,
                    Loan_History.Loan_From AS Loan_Start_Date
                FROM Equipment_List
                JOIN Loan_History ON Equipment_List.Equipment_ID = Loan_History.Equipment_ID
                """
                all_data = pd.read_sql_query(query, conn)
                st.write(all_data)
            except Exception as e:
                st.write("Error fetching data:", e)

        with tab4:
            st.write("Find Available Equipment")

            # Selectbox for Type
            selected_type_label = st.selectbox(
                'Please select an equipment type', ['ALL'] + types
            )

            # Availability options
            availability_options = ["All", "Yes", "No"]
            selected_availability = st.selectbox(
                'Select availability', availability_options
            )
            # Confirm button
            if st.button('Confirm ✅'):
                availability_filter = "All" if selected_availability == "All" else ('Yes' if selected_availability == 'Yes' else 'No')
                try:
                    filtered_data = fetch_equipment_data(conn, availability_filter, selected_type_label)
                    if filtered_data.empty:
                        st.write("No data found for the selected criteria.")
                    else:
                        st.write(filtered_data)
                except Exception as e:
                    st.write("Error executing query:", e)

# Tab for updating Loan History
elif st.session_state.active_page == "Equipment Loan & Return":
    st.title("Update Loan History Availability")
    st.subheader("Select items to mark them as loaned out.")

    with get_database_connection() as conn:
        types = fetch_types(conn)  # Fetch types for filtering

        tab5, tab6 = st.tabs(["Loan Equipment", "Return Equipment"])

        with tab5:
            # Allow user to select a type for filtering available items
            selected_type = st.selectbox("Select Equipment Type", ['ALL'] + types)

            # Query to fetch available equipment based on selected type
            available_data = fetch_equipment_data(conn, 'Yes', selected_type)

            if not available_data.empty:
                # Create a checkbox for each available equipment
                selected_items = st.multiselect(
                    "Select Equipment to Loan Out",
                    options=available_data['EquipmentList_ID'],
                    format_func=lambda x: f"{available_data.loc[available_data['EquipmentList_ID'] == x, 'Equipment_Name'].values[0]} ({x})"
                )

                # Input for Loan_From
                loan_from_date = st.text_input("Enter the Loan From date (e.g., YYYY-MM-DD)")

                # Confirm button
                if st.button("Confirm Loan"):
                    if selected_items and loan_from_date:
                        for equipment_id in selected_items:
                            # Update Loan_History to set Availability to 'No' and set Loan_From
                            update_query = """
                            UPDATE Loan_History
                            SET Availability = 'No', Loan_From = ?
                            WHERE Equipment_ID = ?
                            """
                            try:
                                conn.execute(update_query, (loan_from_date, equipment_id))
                                conn.commit()
                                st.success(f"Updated availability for Equipment ID {equipment_id}.")
                            except Exception as e:
                                st.error(f"Error updating Equipment ID {equipment_id}: {e}")
                    else:
                        st.error("Please select at least one item and enter a Loan From date.")
            else:
                st.write("No available equipment to loan out.")

        with tab6:
            # Allow user to select a type for filtering unavailable items
            selected_type = st.selectbox("Select Equipment Type for Return", ['ALL'] + types)

            # Query to fetch unavailable equipment based on selected type
            unavailable_data = fetch_equipment_data(conn, 'No', selected_type)

            # Store selected items in session state to persist their value
            if 'selected_items_return' not in st.session_state:
                st.session_state.selected_items_return = []

            if not unavailable_data.empty:
                # Create a checkbox for each unavailable equipment
                selected_items_return = st.multiselect(
                    "Select Equipment to Return",
                    options=unavailable_data['EquipmentList_ID'],
                    format_func=lambda x: f"{unavailable_data.loc[unavailable_data['EquipmentList_ID'] == x, 'Equipment_Name'].values[0]} ({x})",
                    default=st.session_state.selected_items_return  # Set default to persist selection
                )

                # Update session state based on selected items
                st.session_state.selected_items_return = selected_items_return


                # Confirm button for returning equipment
                if st.button("Confirm Return"):
                    for equipment_id in st.session_state.selected_items_return:
                        # Update Loan_History to set Availability to 'Yes'
                        update_query = """
                        UPDATE Loan_History
                        SET Availability = 'Yes', Loan_From = NULL
                        WHERE Equipment_ID = ?
                        """
                        try:
                            conn.execute(update_query, (equipment_id,))
                            conn.commit()
                            st.success(f"Updated availability for Equipment ID {equipment_id}.")
                        except Exception as e:
                            st.error(f"Error updating Equipment ID {equipment_id}: {e}")
            else:
                st.write("No unavailable equipment to return.")

else:
    st.write("Welcome! Please navigate using the buttons.")
