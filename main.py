import streamlit as st
from datetime import date
import pandas as pd
import plotly.express as px
import pyodbc
import os

st.markdown("<h1 style='text-align: center; color: gray;'>Finance Performance Tracking</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Expenses", "Analysis"])

# Get database credentials from environment variables
SERVER = os.getenv("SERVER")
DATABASE = os.getenv("DATABASE")
USERNAME = os.getenv("DB_USERNAME")
PASSWORD = os.getenv("PASSWORD")
DRIVER = "{ODBC Driver 17 for SQL Server}"

# Define the connection
def get_connection():
    """Establishes connection to Azure SQL Database"""
    try:
        conn = pyodbc.connect(
            f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}"
        )
        print("✅ Connection successful!")
        return conn
    except pyodbc.Error as e:
            print("❌ Connection failed:", e)
            raise
# Load data from Azure
@st.cache_data
def load_data():
    conn = get_connection()
    query = "SELECT date, amount, category, description FROM Expenses"
    df = pd.read_sql(query,conn)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    conn.close()
    return df

def reset_form():
    """Clears form fields in session state and refreshes UI."""
    for key in ["selected_date", "value", "spending_type", "category", "comments"]:
        if key in st.session_state:
            del st.session_state[key]  # Remove keys individually
    st.rerun()  # Refresh UI

# Initialize session state variables if they don't exist
if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()
if "value" not in st.session_state:
    st.session_state.value = 0.0
if "spending_type" not in st.session_state:
    st.session_state.spending_type = "Recurring"
if "category" not in st.session_state:
    st.session_state.category = "Grocery Shopping"
if "comments" not in st.session_state:
    st.session_state.comments = ""

#Expenses tab contains the form to input spending information
with tab1:
    st.markdown("<h1 style='text-align: Left; color: red;'>Expenses</h1>", unsafe_allow_html=True)
    st.write("Please introduce the expense information:")

    with st.form("Spends Form"):
        selected_date = st.date_input("Select a date", value=st.session_state.selected_date, key="selected_date")
        value = st.number_input("Enter an amount", min_value=0.0, format="%.2f", key="value")
        category = st.selectbox("Select a category", ["Grocery Shopping", "Bills", "Home", "Health", "Transport", "Debt", "Shopping/Fun"], key="category")
        comments = st.text_input("Comments", key="comments")
        submitted = st.form_submit_button("Submit")

        if submitted:
            conn = get_connection()
            cursor = conn.cursor()

            insert_query = """
            INSERT INTO Expenses (date, amount, category, description)
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(insert_query, (selected_date, value, category, comments))
            conn.commit()
            conn.close()

            st.success("Expense added succesfully")
            st.cache_data.clear()
            # Reset the form values trigger a UI refresh
            reset_form()

# Load data BEFORE using df in Analysis tab
df = load_data()

#Analysis tab contains several visualizations and tables to properly analyse spending
with tab2:
    st.markdown("<h2 style='text-align: Left; color: green;'>Analysis</h2>", unsafe_allow_html=True)

    if df.empty:
            st.warning("No data available. Please add expenses first.")
    else:
        # Filter Controls
        years = sorted(df["year"].unique(), reverse=True)
        months = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                   7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}

        selected_year = st.multiselect("Select Year(s)", options=sorted(df["year"].unique(), reverse=True), default=[df["year"].max()])  # Default to latest year
        selected_month = st.multiselect("Select Month(s)", options=months.values(), default=months.values())
        selected_category = st.selectbox("Select Category", options=["All"] + df["category"].unique().tolist(), index=0)

        # Apply Filters
        filtered_df = df[df["year"].isin(selected_year)]

        filtered_df = df[df["year"].isin(selected_year)] if selected_year else df
        filtered_df = filtered_df[filtered_df["month"].isin([k for k, v in months.items() if v in selected_month])] if selected_month else filtered_df
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_category]

        # Add Total Spending Metric
        st.markdown("<h4 style='text-align: Left; color: lightgreen;'>Total Spending</h4>", unsafe_allow_html=True)
        st.metric(label="Total Spending",label_visibility="hidden",value=f"${filtered_df['amount'].sum():,.2f}")
    
        # Line Chart (Total Spending by Month)
        st.markdown("<h4 style='text-align: Left; color: lightgreen;'>Monthly Spending Trend</h4>", unsafe_allow_html=True)
        line_data = df.groupby(["year", "month", "category"])["amount"].sum().reset_index()
        line_data = line_data[line_data["year"].isin(selected_year)]
        line_data["month"] = line_data["month"].map(months)

        ##if selected_month != "All":
        ##    line_data = line_data[line_data["Month"] == month_number]
        
        #if selected_category != "All":
        #    line_data = line_data[line_data["category"] == selected_category]
        line_data = df.groupby(["year", "month"])["amount"].sum().reset_index()
        line_data["month"] = line_data["month"].map(months)  # Convert numbers to month names

        fig_line = px.line(line_data, x="month", y="amount", text='amount',markers=True, labels={"amount": "Total Spending"},
                        title="Total Spending by Month")
        fig_line.update_traces(textposition = "top center", texttemplate = "$%{y:,.0f}")
        st.plotly_chart(fig_line, use_container_width=True)

        # Pie Chart (Spending by Category)
        st.markdown("<h4 style='text-align: Left; color: lightgreen;'>Spending by Category</h4>", unsafe_allow_html=True)
        pie_data = filtered_df.groupby("category")["amount"].sum().reset_index()

        fig_pie = px.pie(pie_data, values="amount", names="category", title="Spending Distribution by Category")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Display Filtered Table
        st.markdown("<h4 style='text-align: Left; color: lightgreen;'>Expenses Details</h4>", unsafe_allow_html=True)
        st.dataframe(filtered_df[["date", "amount", "category", "description"]])