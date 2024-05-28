import streamlit as st
import openai

# Function to set OpenAI API key
def set_openai_api_key(api_key: str):
    openai.api_key = api_key

# Function to generate responses using OpenAI's ChatCompletion API
def get_response(prompt):
    """
    This function uses OpenAI's ChatCompletion API to generate SQL based on a natural language prompt.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant skilled in SQL."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        # Extracting the response text
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        # Error handling to catch common issues like API errors
        return f"An error occurred: {str(e)}"

# Predefined schemas
schemas = {
    "Library System": "CREATE TABLE books (id INT, title VARCHAR(100), author VARCHAR(100), year INT, genre VARCHAR(50));\n"
                      "CREATE TABLE authors (id INT, name VARCHAR(100), birth_year INT);",
    "School System": "CREATE TABLE students (id INT, name VARCHAR(100), grade INT, age INT);\n"
                     "CREATE TABLE courses (id INT, name VARCHAR(100), instructor VARCHAR(100));"
}

# Title and description
st.title("SQL Question Generator")
st.write("Generate SQL questions based on a specific domain and difficulty level.")

# OpenAI API key input
api_key = st.text_input("Enter your OpenAI API key", type="password")
if api_key:
    set_openai_api_key(api_key)

# Schema input
schema_option = st.selectbox("Select a schema or input your own", list(schemas.keys()) + ["Custom"])
if schema_option == "Custom":
    schema = st.text_area("Input your database schema")
else:
    schema = schemas[schema_option]

# Display the selected or input schema in a separate text area
st.text_area("Database Schema", schema, height=200, key="schema_display", disabled=schema_option != "Custom")

# Difficulty level and SQL statements
difficulty_levels = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
sql_statements_options = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "HAVING"]
difficulty_level = st.selectbox("Select difficulty level", difficulty_levels)
sql_statements = st.multiselect("Select SQL statements to include", sql_statements_options)

# Number of questions
num_questions = st.number_input("Number of questions", min_value=1, max_value=100, value=10)

# Generate questions button
if st.button("Generate Questions"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    else:
        # Function to generate questions using OpenAI
        def generate_questions(schema, difficulty, statements, num):
            questions = []
            for i in range(num):
                prompt = f"Generate an SQL question for a database with the following schema:\n\n{schema}\n\n"
                prompt += f"Difficulty: {difficulty}\n"
                prompt += f"SQL statements to include: {', '.join(statements)}\n\n"
                prompt += "Question:"
                question = get_response(prompt)
                questions.append(question)
            return questions
        
        questions = generate_questions(schema, difficulty_level, sql_statements, num_questions)
        
        st.write("### Generated Questions:")
        for i, question in enumerate(questions, 1):
            st.write(f"{i}. {question}")

