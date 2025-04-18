import streamlit as st
import requests
import json
import os
import pandas as pd
from typing import Optional

# Constants
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Set page configuration
st.set_page_config(
    page_title="SQL Database Query Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .query-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .result-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
    }
    .header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1E3A8A;
    }
    .subheader {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "database_uploaded" not in st.session_state:
    st.session_state.database_uploaded = False
if "db_tables" not in st.session_state:
    st.session_state.db_tables = []
if "schema_info" not in st.session_state:
    st.session_state.schema_info = None
if "query_history" not in st.session_state:
    st.session_state.query_history = []

# Helper functions
def upload_database(file, api_key: Optional[str] = None):
    """Upload a database file to the backend API"""
    files = {"db_file": file}
    data = {}
    
    if api_key:
        data["api_key"] = api_key
    
    try:
        response = requests.post(
            f"{API_URL}/upload-database/",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.database_uploaded = True
            st.session_state.db_tables = result.get("tables", [])
            return True, "Database uploaded successfully!"
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    
    except Exception as e:
        return False, f"Error connecting to the backend: {str(e)}"

def get_schema_info():
    """Get schema information from the backend API"""
    try:
        response = requests.get(f"{API_URL}/schema/")
        
        if response.status_code == 200:
            st.session_state.schema_info = response.json().get("schema", {})
            return True
        else:
            return False
    
    except Exception as e:
        st.error(f"Error fetching schema: {str(e)}")
        return False

def query_database(question):
    """Send a natural language query to the backend API"""
    try:
        response = requests.post(
            f"{API_URL}/query/",
            json={"question": question}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Add to query history
            st.session_state.query_history.append({
                "question": question,
                "answer": result.get("answer", "No answer provided")
            })
            
            return True, result
        else:
            return False, f"Error: {response.json().get('detail', 'Unknown error')}"
    
    except Exception as e:
        return False, f"Error connecting to the backend: {str(e)}"

# Main Streamlit app
st.markdown("<div class='header'>SQL Database Query Assistant</div>", unsafe_allow_html=True)
st.markdown(
    "Upload a SQLite database and ask questions in natural language. "
    "The AI will generate SQL queries and provide answers based on your database."
)

# Sidebar with settings and information
with st.sidebar:
    st.markdown("<div class='subheader'>Settings</div>", unsafe_allow_html=True)
    
    api_key = st.text_input(
        "GROQ API Key", 
        type="password", 
        help="Enter your GROQ API key. This will be used to initialize the AI agent."
    )
    
    st.markdown("<div class='subheader'>About</div>", unsafe_allow_html=True)
    st.markdown(
        "This application uses LangChain, LangGraph, and Groq to create an AI agent "
        "that can understand your database schema and answer questions about your data."
    )
    
    st.markdown("<div class='subheader'>Query History</div>", unsafe_allow_html=True)
    if st.session_state.query_history:
        for i, item in enumerate(st.session_state.query_history):
            with st.expander(f"Q: {item['question'][:50]}..."):
                st.markdown(f"**Question:** {item['question']}")
                st.markdown(f"**Answer:** {item['answer']}")
    else:
        st.markdown("No queries yet. Ask a question to get started!")

# Database upload section
st.markdown("<div class='subheader'>Upload Database</div>", unsafe_allow_html=True)
with st.container():
    st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload a SQLite database (.db file)", type=["db"])
    
    if uploaded_file is not None:
        if st.button("Upload and Initialize AI Agent"):
            with st.spinner("Uploading database and initializing AI agent..."):
                success, message = upload_database(uploaded_file, api_key)
                if success:
                    st.success(message)
                    if get_schema_info():
                        st.success("Schema information retrieved successfully!")
                else:
                    st.error(message)
    
    st.markdown("</div>", unsafe_allow_html=True)

# Display database information if uploaded
# if st.session_state.database_uploaded:
#     with st.expander("Database Information", expanded=True):
#         st.markdown("<div class='subheader'>Database Tables</div>", unsafe_allow_html=True)
#         st.write(", ".join(st.session_state.db_tables))
        
#         if st.session_state.schema_info:
#             st.markdown("<div class='subheader'>Schema Information</div>", unsafe_allow_html=True)
            
#             for table_name, table_info in st.session_state.schema_info.items():
#                 with st.expander(f"Table: {table_name}"):
#                     # Display columns
#                     columns_df = pd.DataFrame([
#                         {"Column": col["name"], "Type": col["type"]} 
#                         for col in table_info["columns"]
#                     ])
#                     st.markdown("**Columns:**")
#                     st.dataframe(columns_df)
                    
#                     # Display sample data
#                     if table_info["sample_data"]:
#                         st.markdown("**Sample Data:**")
#                         st.dataframe(pd.DataFrame(table_info["sample_data"]))

# Display database information if uploaded
if st.session_state.database_uploaded:
    # Replace the expander with a regular section
    st.markdown("<div class='subheader'>Database Information</div>", unsafe_allow_html=True)
    
    # Display tables without an outer expander
    st.markdown("<div class='subheader'>Database Tables</div>", unsafe_allow_html=True)
    st.write(", ".join(st.session_state.db_tables))
    
    if st.session_state.schema_info:
        st.markdown("<div class='subheader'>Schema Information</div>", unsafe_allow_html=True)
        
        # Now the table expanders are not nested
        for table_name, table_info in st.session_state.schema_info.items():
            with st.expander(f"Table: {table_name}"):
                # Display columns
                columns_df = pd.DataFrame([
                    {"Column": col["name"], "Type": col["type"]} 
                    for col in table_info["columns"]
                ])
                st.markdown("**Columns:**")
                st.dataframe(columns_df)
                
                # Display sample data
                if "sample_data" in table_info and table_info["sample_data"]:
                    st.markdown("**Sample Data:**")
                    st.dataframe(pd.DataFrame(table_info["sample_data"]))

# Query section
if st.session_state.database_uploaded:
    st.markdown("<div class='subheader'>Ask a Question</div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='query-section'>", unsafe_allow_html=True)
        
        question = st.text_input(
            "Enter your question about the database",
            placeholder="e.g., 'What are the names of employees with a salary over 50000?'"
        )
        
        if st.button("Submit Question"):
            if question:
                with st.spinner("Generating answer..."):
                    success, result = query_database(question)
                    
                    if success:
                        st.markdown("<div class='result-section'>", unsafe_allow_html=True)
                        st.markdown("### Answer")
                        st.markdown(result.get("answer", "No answer generated"))
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.error(result)
            else:
                st.warning("Please enter a question.")
        
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Example Questions")
        example_questions = [
            "What are all the tables in the database?",
            "How many employees are there?",
            "What is the average salary of employees?",
            "Which employee has the highest salary?",
            "Show me the information about orders with amount greater than 200"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{hash(question)}"):
                with st.spinner("Generating answer..."):
                    success, result = query_database(question)
                    
                    if success:
                        st.markdown("<div class='result-section'>", unsafe_allow_html=True)
                        st.markdown("<div class='result-section'>", unsafe_allow_html=True)
                        st.markdown("### Answer")
                        st.markdown(result.get("answer", "No answer generated"))
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.error(result)
        
        # Tips for better questions
        with st.expander("Tips for Better Questions"):
            st.markdown("""
            - Be specific about what information you're looking for
            - Mention the table name if you know it
            - For numerical data, specify if you want aggregations (sum, average, etc.)
            - Provide context in your question (e.g., time periods, specific conditions)
            """)

# Main application execution point
if __name__ == "__main__":
    # Display welcome message if no database is uploaded
    if not st.session_state.database_uploaded:
        st.info(
            "Welcome to the SQL Database Query Assistant! "
            "Start by uploading a SQLite database file (.db) using the uploader above."
        )