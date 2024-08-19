#25/7
import streamlit as st
import openai
import psycopg2
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, text, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import base64
import xml.etree.ElementTree as ET
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
                model="gpt-4o",
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
        "sample_data": [
            "INSERT INTO movies (id, title, director, genre, release_year) VALUES (1, 'Inception', 'Christopher Nolan', 'Sci-Fi', 2010);",
            "INSERT INTO movies (id, title, director, genre, release_year) VALUES (2, 'The Dark Knight', 'Christopher Nolan', 'Action', 2008);",
            "INSERT INTO movies (id, title, director, genre, release_year) VALUES (3, 'Pulp Fiction', 'Quentin Tarantino', 'Crime', 1994);",
            "INSERT INTO movies (id, title, director, genre, release_year) VALUES (4, 'The Matrix', 'The Wachowskis', 'Sci-Fi', 1999);",
            "INSERT INTO movies (id, title, director, genre, release_year) VALUES (5, 'The Godfather', 'Francis Ford Coppola', 'Crime', 1972);"
        ]
    },
    "School System": {
        "schema": "CREATE TABLE IF NOT EXISTS students (id INT, name VARCHAR(100), grade INT, age INT);\n"
                  "CREATE TABLE IF NOT EXISTS courses (id INT, name VARCHAR(100), instructor VARCHAR(100));",
        "sample_data": [
            "INSERT INTO students VALUES (1, 'Alice', 10, 15);",
            "INSERT INTO students VALUES (2, 'Bob', 12, 17);",
            "INSERT INTO courses VALUES (1, 'Math', 'Dr. Smith');",
            "INSERT INTO courses VALUES (2, 'Science', 'Dr. Johnson');"
        ]
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
            for command in schema_info["sample_data"]:
                if command.strip():
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
        st.session_state.sample_data = ""

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
            sample_data = st.text_area("Input sample data commands")
        else:
            schema = schemas[schema_option]["schema"]
            sample_data = "\n".join(schemas[schema_option]["sample_data"])

        if st.button("Show Sample Data"):
            st.session_state.show_sample_data = True
            st.session_state.schema = schema
            st.session_state.sample_data = sample_data
            st.experimental_rerun()

    if st.session_state.show_sample_data:
        st.code(st.session_state.schema)
        st.code(st.session_state.sample_data)
        
        if st.button("Hide Sample Data"):
            st.session_state.show_sample_data = False
            st.experimental_rerun()

    def clean_response(response):
        cleaned_response = response.replace('**', '').strip()
        return cleaned_response

    def generate_questions(schema, difficulty, statements, num):
        questions = []
        solutions = []
        for i in range(num):
            prompt = (
                f"Generate an SQL question for a database with the following schema:\n\n{schema}\n\n"
                f"Difficulty: {difficulty}\nSQL statements to include: {', '.join(statements)}\n\n"
                "Question and Solution:"
            )
            if difficulty == "Level 5" and "JOIN" in statements:
                prompt += "Include two JOIN operations in the question.\n\nQuestion and Solution:"
            else:
                prompt += "Question and Solution:"
            responses = get_response(prompt)
            if len(responses) > 0:
                question_text = clean_response(responses[0].split('Solution:')[0].strip())
                solution_texts = [clean_response(response.split('Solution:')[1].strip().replace('```', '').strip()) for response in responses if 'Solution:' in response]
                if solution_texts:
                    solutions.append(solution_texts[0])
                else:
                    solutions.append("No solution available.")
                questions.append(question_text)
            else:
                questions.append("No question generated.")
                solutions.append("No solution available.")
        return questions, solutions

    def validate_questions(questions, solutions, difficulty, statements):
        validated_questions = []
        validated_solutions = []
        for question, solution_set in zip(questions, solutions):
            if validate_question(question, solution_set, difficulty, statements):
                validated_questions.append(question)
                validated_solutions.append(solution_set)
            else:
                # Regenerate the question if it does not meet the criteria
                new_question, new_solution_set = regenerate_question(difficulty, statements)
                validated_questions.append(new_question)
                validated_solutions.append(new_solution_set)
        return validated_questions, validated_solutions

    def validate_question(question, solution_set, difficulty, statements):
        # Implement validation logic based on difficulty and SQL statements
        # Return True if the question is valid, otherwise False
        return True  # Placeholder implementation

    def regenerate_question(difficulty, statements):
        prompt = (
            f"Regenerate an SQL question with difficulty: {difficulty}\n"
            f"SQL statements to include: {', '.join(statements)}\n\n"
            "Question and Solution:"
        )
        responses = get_response(prompt)
        if len(responses) > 0:
            question_text = clean_response(responses[0].split('Solution:')[0].strip())
            solution_texts = [clean_response(response.split('Solution:')[1].strip()) for response in responses if 'Solution:' in response]
            if solution_texts:
                return question_text, solution_texts
        return "No question generated.", ["No solution available."]

    if st.button("Generate Questions"):
        toggle_settings()
        with st.spinner("Generating questions..."):
            questions, solutions = generate_questions(st.session_state.schema, difficulty_level, sql_statements, num_questions)
        with st.spinner("Validating questions..."):
            validated_questions, validated_solutions = validate_questions(questions, solutions, difficulty_level, sql_statements)
        
        # Save generated questions to the database
        session = Session()
        for question_text, solution_text in zip(validated_questions, validated_solutions):
            new_question = Question(text=question_text, solution=solution_text)
            session.add(new_question)
        session.commit()
        session.close()
        
        st.session_state.questions = validated_questions  # Store validated questions in session state
        st.session_state.solutions = validated_solutions  # Store validated solutions in session state
        st.balloons() 
# Display questions, solutions, and collect feedback independently for each
if 'questions' in st.session_state:
    edited_questions = []
    edited_solutions = []
    for i, (question, solution) in enumerate(zip(st.session_state.questions, st.session_state.solutions), 1):
        st.write(f'<h3 style="color: #000000;"> Question {i}</h3>', unsafe_allow_html=True)
        edited_question = st.text_area(f"Edit Question {i}", question, key=f"edit_question_{i}", height=150)
        st.write('<h4 style="color: #000000;">Solution:</h4>', unsafe_allow_html=True)
        #st.write(f'<label style="font-size: 20px; color: #362624;">Solution {i}</label>', unsafe_allow_html=True)
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

    def export_to_xml(questions, solutions):
        quiz = ET.Element('quiz')

        for i, (question, solution_set) in enumerate(zip(questions, solutions), 1):
            question_element = ET.SubElement(quiz, 'question', type="coderunner")

            name = ET.SubElement(question_element, 'name')
            text = ET.SubElement(name, 'text')
            text.text = f"Question {i}"

            questiontext = ET.SubElement(question_element, 'questiontext', format="html")
            text = ET.SubElement(questiontext, 'text')
            text.text = f"<![CDATA[<p>{question}</p>]]>"

            generalfeedback = ET.SubElement(question_element, 'generalfeedback', format="html")
            text = ET.SubElement(generalfeedback, 'text')
            text.text = ""

            defaultgrade = ET.SubElement(question_element, 'defaultgrade')
            defaultgrade.text = "1.0000000"

            penalty = ET.SubElement(question_element, 'penalty')
            penalty.text = "0.0000000"

            hidden = ET.SubElement(question_element, 'hidden')
            hidden.text = "0"

        # Assuming the first solution is the correct one
            answer = ET.SubElement(question_element, 'answer')
            cleaned_solution = solution.replace('```', '').strip()
            answer.text = cleaned_solution

            testcases = ET.SubElement(question_element, 'testcases')

            # Add a test case (example)
            testcase = ET.SubElement(testcases, 'testcase', testtype="0", useasexample="1", hiderestiffail="0", mark="1.0000000")
            testcode = ET.SubElement(testcase, 'testcode')
            text = ET.SubElement(testcode, 'text')
            text.text = "-- Testing with original db"

            stdin = ET.SubElement(testcase, 'stdin')
            text = ET.SubElement(stdin, 'text')
            text.text = ""

            expected = ET.SubElement(testcase, 'expected')
            text = ET.SubElement(expected, 'text')
            text.text = "EXPECTED OUTPUT HERE"  # Replace with actual expected output

            extra = ET.SubElement(testcase, 'extra')
            text = ET.SubElement(extra, 'text')
            text.text = ""

            display = ET.SubElement(testcase, 'display')
            text = ET.SubElement(display, 'text')
            text.text = "SHOW"

        return ET.tostring(quiz, encoding='unicode')

    if st.button("Export to XML"):
        if 'questions' in st.session_state:
            xml_content = export_to_xml(st.session_state.questions, st.session_state.solutions)
            st.download_button(label="Download XML", data=xml_content, file_name=f"{filename}.xml")
        st.success("Exported questions to XML file successfully!")
        st.balloons() 

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
