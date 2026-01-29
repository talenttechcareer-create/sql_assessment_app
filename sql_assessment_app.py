import streamlit as st
import pandas as pd
import random
import uuid
from datetime import datetime
from db_sandbox import create_sandbox
import sqlite3

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(
    page_title="SQL Assessment",
    page_icon="🗄️",
    layout="wide"
)

st.title("🗄️ SQL Assessment Platform")
st.subheader("👤 Candidate Information")

# Candidate info
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Full Name", key="name")
with col2:
    email = st.text_input("Email Address", key="email")

st.divider()

# ---------------------------
# ERD / Table Schema (One per Candidate)
# ---------------------------
st.subheader("🗂️ Database Schema / ERD")
with st.expander("📊 ERD & Table Metadata", expanded=True):
    st.code("""
CITY
┌─────────────┐
│ id (PK)     │
│ name        │
│ countrycode │
│ population  │
└─────────────┘

tweets
┌─────────────┐
│ tweet_id(PK)│
│ user_id     │
│ msg         │
│ tweet_date  │
└─────────────┘

departments
┌─────────────┐
│ id (PK)     │
│ dept_name   │
└─────────────┘

employees
┌─────────────┐
│ id (PK)     │
│ name        │
│ dept_id(FK) │ → departments.id
│ salary      │
└─────────────┘
""", language="text")

st.divider()

# ---------------------------
# Load Question Bank
# ---------------------------
try:
    question_df = pd.read_csv("question_bank.csv")
except FileNotFoundError:
    st.error("❌ question_bank.csv not found. Please add it to the project folder.")
    st.stop()

# ---------------------------
# Randomize Questions by Difficulty
# ---------------------------
num_questions_per_difficulty = {'beginner':2, 'medium':2, 'hard':1}  # Example
sample_questions = pd.DataFrame()

for diff, num in num_questions_per_difficulty.items():
    df_diff = question_df[question_df['difficulty']==diff]
    if len(df_diff) > 0:
        n = min(num, len(df_diff))
        sample_questions = pd.concat([sample_questions, df_diff.sample(n=n, random_state=random.randint(1,1000))])

sample_questions.reset_index(drop=True, inplace=True)

# Dictionary to store candidate queries
candidate_answers = {}

st.subheader("💻 SQL Questions (Follow the Flow)")

# ---------------------------
# Display questions with expander
# ---------------------------
for i, row in sample_questions.iterrows():
    with st.expander(f"Q{i+1}: {row['difficulty'].capitalize()} - {row['question_text']}", expanded=True):
        st.markdown(f"**Table Reference:** {row['table_reference']}")
        if pd.notna(row['example_input']):
            st.markdown(f"**Example Input:**\n```\n{row['example_input']}\n```")
        if pd.notna(row['example_output']):
            st.markdown(f"**Expected Output:**\n```\n{row['example_output']}\n```")

        candidate_answers[row['id']] = st.text_area(
            "Your SQL Query:", 
            height=150,
            key=f"sql_{row['id']}"
        )

        # Optional SQLite test for this question
        conn = create_sandbox()
        if st.button(f"Run Query for Q{i+1}", key=f"run_{row['id']}"):
            query = candidate_answers[row['id']]
            if query.strip()=="":
                st.warning("Enter a SQL query to test.")
            else:
                try:
                    df_result = pd.read_sql(query, conn)
                    st.dataframe(df_result)
                except Exception as e:
                    st.error(f"SQL Error: {e}")

# ---------------------------
# Submit Assessment
# ---------------------------
if st.button("✅ Submit Assessment", key="submit"):
    if not name or not email:
        st.error("Please enter your name and email.")
    else:
        session_id = str(uuid.uuid4())
        submission_data = {
            "Name": name,
            "Email": email,
            "Session ID": session_id,
            "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        for qid, answer in candidate_answers.items():
            submission_data[f"Q{qid}"] = answer

        submission_file = f"submissions/{session_id}.csv"
        pd.DataFrame([submission_data]).to_csv(submission_file, index=False)

        st.success(f"🎉 Assessment submitted! Your unique session ID: {session_id}")
        st.info("You can safely close the browser. Your results are stored securely.")
