import streamlit as st
import pandas as pd
import sqlite3
from transformers import BlenderbotTokenizer
from transformers import BlenderbotForConditionalGeneration


# Initialize the model and tokenizer
@st.experimental_singleton
def get_models():
    model_name = "facebook/blenderbot-400M-distill"
    tokenizer = BlenderbotTokenizer.from_pretrained(model_name)
    model = BlenderbotForConditionalGeneration.from_pretrained(model_name)
    return tokenizer, model

# Function to generate chatbot responses
def generate_response(user_input):
    tokenizer, model = get_models()
    inputs = tokenizer(user_input, return_tensors="pt")
    result = model.generate(**inputs)
    response = tokenizer.decode(result[0], skip_special_tokens=True)
    return response

# Chat interface initialization
message = st.chat_message("ai")
message.write("你好！我是 ChatBot Rex-iv，可以回答問題及提供這個數據庫的資訊。")

# User input area
user_input = st.chat_input("Say something...")
if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    # Generate and display the response from the AI
    bot_response = generate_response(user_input)
    with st.chat_message("assistant"):
        st.write(bot_response)

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

    if availability != 'All':
        query_conditions.append('Loan_History.Availability = ?')
        params.append(availability)

    if equipment_type != 'ALL':
        query_conditions.append("Equipment_List.Type = ?")
        params.append(equipment_type)

    availability_condition = ' AND '.join(query_conditions) if query_conditions else '1=1'

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
    st.session_state.active_page = "Overview"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Track if the login expander is open
if 'login_expander_open' not in st.session_state:
    st.session_state.login_expander_open = True

st.markdown(
    """
    <style>
    .stButton > button {
        min-width: 200px; 
        width: 200px;      
        height: 40px;     
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
                st.session_state.login_expander_open = False
                st.session_state.active_page = "Equipment Loan & Return"
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
    tab1 = st.tabs(["Information"])[0]
    with tab1:
        st.title('Overview:')
        st.subheader('This is a test page for viewing equipment')

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

            selected_type_label = st.selectbox(
                'Please select an equipment type', ['ALL'] + types
            )

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
        types = fetch_types(conn)

        tab5, tab6 = st.tabs(["Loan Equipment", "Return Equipment"])

        with tab5:
            selected_type = st.selectbox("Select Equipment Type", ['ALL'] + types)

            available_data = fetch_equipment_data(conn, 'Yes', selected_type)

            if not available_data.empty:
                selected_items = st.multiselect(
                    "Select Equipment to Loan Out",
                    options=available_data['EquipmentList_ID'],
                    format_func=lambda x: f"{available_data.loc[available_data['EquipmentList_ID'] == x, 'Equipment_Name'].values[0]} ({x})"
                )

                loan_from_date = st.text_input("Enter the Loan From date (e.g., YYYY-MM-DD)")

                if st.button("Confirm Loan"):
                    if selected_items and loan_from_date:
                        for equipment_id in selected_items:
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
            selected_type = st.selectbox("Select Equipment Type for Return", ['ALL'] + types)

            unavailable_data = fetch_equipment_data(conn, 'No', selected_type)

            if 'selected_items_return' not in st.session_state:
                st.session_state.selected_items_return = []

            if not unavailable_data.empty:
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
