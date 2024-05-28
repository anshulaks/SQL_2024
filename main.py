import streamlit as st
import openai
import base64

@st.cache_data
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


img = get_img_as_base64("image.jpg")

page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://images.unsplash.com/photo-1501426026826-31c667bdf23d");
background-size: 180%;
background-position: top left;
background-repeat: no-repeat;
background-attachment: local;
}}

[data-testid="stSidebar"] > div:first-child {{
background-image: url("data:image/png;base64,{img}");
background-position: center; 
background-repeat: no-repeat;
background-attachment: fixed;
}}

[data-testid="stHeader"] {{
background: rgba(0,0,0,0);
}}

[data-testid="stToolbar"] {{
right: 2rem;
}}
</style>
"""

st.markdown(page_bg_img, unsafe_allow_html=True)
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
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Predefined schemas
schemas = {
    "Library System": "CREATE TABLE books (id INT, title VARCHAR(100), author VARCHAR(100), year INT, genre VARCHAR(50));\n"
                      "CREATE TABLE authors (id INT, name VARCHAR(100), birth_year INT);",
    "School System": "CREATE TABLE students (id INT, name VARCHAR(100), grade INT, age INT);\n"
                     "CREATE TABLE courses (id INT, name VARCHAR(100), instructor VARCHAR(100));"
}

st.title("SQL Question Generator")
st.write("Generate SQL questions based on a specific domain and difficulty level.")

api_key = st.text_input("Enter your OpenAI API key", type="password")
if api_key:
    set_openai_api_key(api_key)

schema_option = st.selectbox("Select a schema or input your own", list(schemas.keys()) + ["Custom"])
if schema_option == "Custom":
    schema = st.text_area("Input your database schema")
else:
    schema = schemas[schema_option]
st.text_area("Database Schema", schema, height=200, key="schema_display", disabled=schema_option != "Custom")

difficulty_levels = ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
sql_statements_options = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "HAVING"]
difficulty_level = st.selectbox("Select difficulty level", difficulty_levels)
sql_statements = st.multiselect("Select SQL statements to include", sql_statements_options)
num_questions = st.number_input("Number of questions", min_value=1, max_value=100, value=10)

def generate_questions(schema, difficulty, statements, num):
    questions = []
    for i in range(num):
        prompt = f"Generate an SQL question for a database with the following schema:\n\n{schema}\n\nDifficulty: {difficulty}\nSQL statements to include: {', '.join(statements)}\n\nQuestion:"
        question = get_response(prompt)
        questions.append(question)
    return questions

if st.button("Generate Questions"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    else:
        questions = generate_questions(schema, difficulty_level, sql_statements, num_questions)
        st.session_state.questions = questions  # Store questions in session state

# Display questions and collect feedback independently for each
if 'questions' in st.session_state:
    for i, question in enumerate(st.session_state.questions, 1):
        st.write(f"{i}. {question}")
        if f"feedback_{i}" not in st.session_state:  # Check if feedback has been submitted for this question
            usefulness = st.slider(f"Rate the usefulness of question {i} (1=Not Useful, 5=Very Useful)", 1, 5, 3, key=f"usefulness_{i}")
            if st.button(f"Submit Feedback for Question {i}", key=f"btn_{i}"):
                st.session_state[f"feedback_{i}"] = usefulness  # Store feedback in session state
                if usefulness == 1:
                    new_question = generate_questions(schema, "Level 5", sql_statements, 1)[0]
                    st.write("### Enhanced SQL Challenge:")
                    st.write(new_question)
                elif usefulness == 2:
                    new_question = generate_questions(schema, "Level 4", sql_statements, 1)[0]
                    st.write("### Enhanced SQL Challenge:")
                    st.write(new_question)
                elif usefulness == 3:
                    new_question = generate_questions(schema, "Level 3", sql_statements, 1)[0]
                    st.write("### Enhanced SQL Challenge:")
                    st.write(new_question)
                elif usefulness == 4:
                    new_question = generate_questions(schema, "Level 4", sql_statements, 1)[0]
                    st.write("### Enhanced SQL Challenge:")
                    st.write(new_question)
                elif usefulness == 5:
                    st.success("Great going buddy!")
