import streamlit as st
import json
import openai
import psycopg2
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, text, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import pandas as pd
import base64
from io import BytesIO

# Load OpenAI API key from secret_key.py
from secret_key import openai_key

# Database setup
Base = declarative_base()

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)

class Schema(Base):
    __tablename__ = 'schemas'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    schema = Column(Text, nullable=False)

DATABASE_URL = "postgresql://postgres:6837@localhost:5432/MainDb"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Function to set OpenAI API key
def set_openai_api_key(api_key: str):
    openai.api_key = api_key

set_openai_api_key(openai_key)

# Function to generate responses using OpenAI's ChatCompletion API
def get_response(prompt, num_responses=3):
    try:
        responses = []
        for _ in range(num_responses):
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an assistant skilled in SQL."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            responses.append(response['choices'][0]['message']['content'].strip())
        return responses
    except Exception as e:
        return [f"An error occurred: {str(e)}"]

# Predefined schemas with sample data
schemas = {
    "Movie Database": {
        "schema": "CREATE TABLE IF NOT EXISTS movies (id INT, title VARCHAR(100), director VARCHAR(100), genre VARCHAR(50), release_year INT);",
        "sample_data": {
            "movies": [
                {"id": 1, "title": 'Inception', "director": 'Christopher Nolan', "genre": 'Sci-Fi', "release_year": 2010},
                {"id": 2, "title": 'The Dark Knight', "director": 'Christopher Nolan', "genre": 'Action', "release_year": 2008},
                {"id": 3, "title": 'Pulp Fiction', "director": 'Quentin Tarantino', "genre": 'Crime', "release_year": 1994},
                {"id": 4, "title": 'The Matrix', "director": 'The Wachowskis', "genre": 'Sci-Fi', "release_year": 1999},
                {"id": 5, "title": 'The Godfather', "director": 'Francis Ford Coppola', "genre": 'Crime', "release_year": 1972}
            ]
        }
    },
    "School System": {
        "schema": "CREATE TABLE IF NOT EXISTS students (id INT, name VARCHAR(100), grade INT, age INT);\n"
                  "CREATE TABLE IF NOT EXISTS courses (id INT, name VARCHAR(100), instructor VARCHAR(100));",
        "sample_data": {
            "students": [
                {"id": 1, "name": 'Alice', "grade": 10, "age": 15},
                {"id": 2, "name": 'Bob', "grade": 12, "age": 17}
            ],
            "courses": [
                {"id": 1, "name": 'Math', "instructor": 'Dr. Smith'},
                {"id": 2, "name": 'Science', "instructor": 'Dr. Johnson'}
            ]
        }
    }
}

# Function to initialize the database with predefined schemas
def initialize_database():
    session = Session()
    for schema_name, schema_info in schemas.items():
        try:
            # Execute schema commands
            for command in schema_info["schema"].split(';'):
                if command.strip():
                    session.execute(text(command))
            # Execute data insertion commands
            for table_name, data in schema_info["sample_data"].items():
                for row in data:
                    columns = ', '.join(row.keys())
                    values = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in row.values()])
                    command = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
                    session.execute(text(command))
            session.commit()
        except Exception as e:
            session.rollback()
            st.error(f"Error initializing {schema_name} schema: {e}")
    session.close()

# Load the image and convert it to base64
def get_image_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_data = get_image_as_base64("image.jpg")
background_image = f"data:image/jpg;base64,{img_data}"

# Create the CSS style
page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
    background-image: url("{background_image}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}
textarea {{
    background-color: #ffffcc !important;  /* Light yellow background */
    font-size: 20px !important;  /* Larger font size */
    color: #362624 !important;
}}
</style>
"""

# Apply the CSS style
st.markdown(page_bg_img, unsafe_allow_html=True)

# Title and description
st.sidebar.title("SQL Question Generator")
st.sidebar.write("Navigate through the pages to generate questions, view history, and manage schemas.")

# Sidebar navigation
page = st.sidebar.radio("Choose a page", ["Home", "Generate Questions", "Questions History", "Saved Schemas"])

if page == "Home":
    st.title("Welcome to the SQL Question Generator!")
    st.write("This application helps you generate SQL questions and solutions based on specific domains and difficulty levels.")

elif page == "Generate Questions":
    st.title("Generate SQL Questions")
    
    # Initialize session state variables
    if 'show_sample_data' not in st.session_state:
        st.session_state.show_sample_data = False
    if 'show_settings' not in st.session_state:
        st.session_state.show_settings = True
    if 'schema' not in st.session_state:
        st.session_state.schema = ""
    if 'sample_data' not in st.session_state:
        st.session_state.sample_data = {}

    def toggle_settings():
        st.session_state.show_settings = not st.session_state.show_settings

    if st.session_state.show_settings:
        col1, col2 = st.columns(2)
        with col1:
            schema_option = st.selectbox("Select a schema or input your own", list(schemas.keys()) + ["Custom"])
        with col2:
            difficulty_level = st.selectbox("Select difficulty level", ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"])

        col3, col4 = st.columns(2)
        with col3:
            sql_statements = st.multiselect("Select SQL statements to include", ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "HAVING", "ORDER BY", "Subqueries"])
        with col4:
            num_questions = st.number_input("Number of questions", min_value=1, max_value=100, value=10)

        if schema_option == "Custom":
            schema = st.text_area("Input your database schema")
            sample_data_input = st.text_area("Input sample data commands (as JSON object with table names as keys and lists of dictionaries as values)")
            try:
                sample_data = json.loads(sample_data_input)
            except json.JSONDecodeError:
                sample_data = {}
        else:
            schema = schemas[schema_option]["schema"]
            sample_data = schemas[schema_option]["sample_data"]

        if st.button("Show Sample Data"):
            st.session_state.show_sample_data = True
            st.session_state.schema = schema
            st.session_state.sample_data = sample_data
            st.experimental_rerun()

    if st.session_state.show_sample_data:
        st.code(st.session_state.schema)
        try:
            for table_name, data in st.session_state.sample_data.items():
                st.write(f"**{table_name}**")
                sample_data_df = pd.DataFrame(data)
                st.table(sample_data_df)
        except ValueError as e:
            st.error(f"Error displaying sample data: {e}")
        
        if st.button("Hide Sample Data"):
            st.session_state.show_sample_data = False
            st.experimental_rerun()

    def clean_response(response):
        cleaned_response = response.replace('**', '').strip()
        return cleaned_response

    def generate_sql_prompt(schema, sample_data, difficulty, statements):
        allowed_statements = ', '.join(statements)
        
        prompt = (
            f"Generate an SQL question and solution in JSON format for a database with the following schema:\n\n{schema}\n\n"
            f"Here is some sample data:\n\n{json.dumps(sample_data, indent=4)}\n\n"#sample data=
            f"Difficulty: {difficulty}\n"#difficulty=make it more readable/reusable code
            f"The SQL should only include the following statements: {allowed_statements}.\n\n"
            "Respond with a JSON object with fields 'question' and 'solution'."
        )
        return prompt

    def validate_sql(sql, allowed_statements):
        allowed_statements = [stmt.upper() for stmt in allowed_statements]
        sql_upper = sql.upper()
        unallowed_statements = ["JOIN", "ORDER BY", "GROUP BY", "HAVING", "SUBQUERY", "UNION"]
        
        for statement in unallowed_statements:
            if statement in sql_upper and statement not in allowed_statements:
                return False
        return True

    def parse_response(response):
        print(f"Raw response: {response}")  # Debugging line
        if not response:
            return "No response received", "No response received"

        try:
            response_json = json.loads(response)
            question = response_json.get('question', '').strip()
            solution = response_json.get('solution', '')

            if isinstance(solution, list):
                solution = solution[0].get('sql', '').strip()
            elif isinstance(solution, str):
                solution = solution.strip()
            else:
                solution = "Invalid solution format"

            return question, solution

        except json.JSONDecodeError:
            # Handle non-JSON formatted responses
            parts = response.split('Solution:')
            if len(parts) == 2:
                question = parts[0].strip()
                solution = parts[1].strip()
                return question, solution
            return "Invalid response format", "Invalid response format"


    def validate_sample_data(schema, sample_data):
        # Add your validation logic here
        # Ensure dates match, authors and genres are consistent, and relationships are valid
        return True

    def generate_and_validate_questions(schema, sample_data, difficulty, statements, num):
        questions = []
        solutions = []
        for _ in range(num):
            prompt = generate_sql_prompt(schema, sample_data, difficulty, statements)
            response = get_response(prompt)
            
            for res in response:
                question_text, solution_text = parse_response(res)
                if validate_sql(solution_text, statements):
                    questions.append(question_text)
                    solutions.append(solution_text)
                    break  # Stop once we have a valid response
            else:
                questions.append("No valid question generated.")
                solutions.append("No valid solution available.")
        return questions, solutions

    def generate_questions_with_retries(schema, sample_data, difficulty, statements, num, max_retries=3):
        questions = []
        solutions = []
        retries = 0

        while len(questions) < num and retries < max_retries:
            generated_questions, generated_solutions = generate_and_validate_questions(schema, sample_data, difficulty, statements, num - len(questions))
            
            for question, solution in zip(generated_questions, generated_solutions):
                if "valid" in question.lower():
                    retries += 1
                    break
                questions.append(question)
                solutions.append(solution)

        if retries == max_retries:
            questions.extend(["Error generating question. Please try again."] * (num - len(questions)))
            solutions.extend(["Error generating solution."] * (num - len(solutions)))

        return questions, solutions

    if st.button("Generate Questions"):
        toggle_settings()
        if validate_sample_data(st.session_state.schema, st.session_state.sample_data):
            with st.spinner("Generating questions..."):
                questions, solutions = generate_questions_with_retries(st.session_state.schema, st.session_state.sample_data, difficulty_level, sql_statements, num_questions)
            
            # Save generated questions to the database
            session = Session()
            for question_text, solution_text in zip(questions, solutions):
                new_question = Question(text=question_text, solution=solution_text)
                session.add(new_question)
            session.commit()
            session.close()
            
            st.session_state.questions = questions  # Store validated questions in session state
            st.session_state.solutions = solutions  # Store validated solutions in session state
            st.balloons()
        else:
            st.error("Sample data validation failed. Please check your sample data and try again.")

# Display questions, solutions, 
if 'questions' in st.session_state:
    edited_questions = []
    edited_solutions = []
    for i, (question, solution) in enumerate(zip(st.session_state.questions, st.session_state.solutions), 1):
        st.write(f'<h3 style="color: #000000;"> Question {i}</h3>', unsafe_allow_html=True)
        edited_question = st.text_area(f"Edit Question {i}", question, key=f"edit_question_{i}", height=150)
        st.write('<h4 style="color: #000000;">Solution:</h4>', unsafe_allow_html=True)
        cleaned_solution = solution.replace('```', '').strip()
        edited_solution = st.text_area(f"Edit Solution {i}", cleaned_solution, key=f"edit_solution_{i}", height=150)
        edited_questions.append(edited_question)
        edited_solutions.append(edited_solution)
    
    # Add a text input for the filename
    filename = st.text_input("Enter the filename (without extension)", value="Assessment_1")

    def download_file(filename, content):
        st.download_button(label=f"Download {filename}", data=content, file_name=filename)

    if st.button("Save and Download"):
        questions_content_md = "\n\n".join(
            [f"### Question {i+1}:\n\n{edited_questions[i]}\n\n**Solution:**\n\n{edited_solutions[i]}" for i in range(len(edited_questions))]
        )
        questions_content_txt = "\n\n".join(
            [f"Question {i+1}:\n\n{edited_questions[i]}\n\nSolution:\n\n{edited_solutions[i]}" for i in range(len(edited_questions))]
        )
        download_file(f"{filename}.md", questions_content_md)
        download_file(f"{filename}.txt", questions_content_txt)

    if st.button("Toggle Settings"):
        toggle_settings()

elif page == "Questions History":
    st.title("Questions History")
    session = Session()
    questions = session.query(Question).all()
    for q in questions:
        st.write(f"**Question {q.id}:** {q.text}")
        st.write(f"**Solution:** {q.solution}")
        if st.button(f"Delete Question {q.id}", key=f"delete_{q.id}"):
            session.execute(delete(Question).where(Question.id == q.id))
            session.commit()
            st.experimental_rerun()
    session.close()

elif page == "Saved Schemas":
    st.title("Saved Schemas")
    
    # Save new schema
    new_schema_name = st.text_input("Schema Name")
    new_schema_content = st.text_area("Schema SQL Commands")
    
    if st.button("Save Schema"):
        if new_schema_name and new_schema_content:
            session = Session()
            new_schema = Schema(name=new_schema_name, schema=new_schema_content)
            session.add(new_schema)
            session.commit()
            session.close()
            st.success("Schema saved successfully!")
        else:
            st.error("Please provide both name and schema content.")

    # Display saved schemas
    session = Session()
    saved_schemas = session.query(Schema).all()
    for schema in saved_schemas:
        st.subheader(schema.name)
        st.code(schema.schema)
        st.button("Copy Schema", key=f"copy_{schema.id}", on_click=st.experimental_set_query_params, kwargs={"schema": schema.schema})
    session.close()

# Initialize the database with predefined schemas
initialize_database()
