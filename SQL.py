import streamlit as st
import json
import openai
from sqlalchemy import create_engine, Column, Integer, String, Text, text, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import base64
import xml.etree.ElementTree as ET
 


# Load OpenAI API key from secret_key.py
openai.api_key = st.secrets["openai_key"]

# Database setup
Base = declarative_base()

class Schema(Base):
    __tablename__ = 'schemas'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    schema_sql = Column(Text, nullable=False)
    sample_data = Column(Text, nullable=False)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)

# SQLite database setup
DATABASE_URL = "sqlite:///your_database.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)



# Function to set OpenAI API key from Streamlit secrets
def set_openai_api_key():
    openai.api_key = st.secrets["openai_key"]

# Set the API key by calling the function
set_openai_api_key()

# Agents
class SchemaAgent:
    def __init__(self, session):
        self.session = session
    
    def initialize_database(self, schemas):
        for schema_name, schema_info in schemas.items():
            try:
                # Save schema and sample data
                schema_sql = schema_info["schema"]
                sample_data = json.dumps(schema_info["sample_data"])
                self.save_schema(schema_name, schema_sql, sample_data)
                # Initialize the database
                for command in schema_sql.split(';'):
                    if command.strip():
                        self.session.execute(text(command))
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                st.error(f"Error initializing {schema_name} schema: {e}")

    def save_schema(self, name, schema_sql, sample_data):
        new_schema = Schema(name=name, schema_sql=schema_sql, sample_data=sample_data)
        self.session.add(new_schema)
        self.session.commit()

    def get_saved_schemas(self):
        return self.session.query(Schema).all()

    def get_schema_and_data(self, name):
        schema = self.session.query(Schema).filter_by(name=name).first()
        if schema:
            return schema.schema_sql, json.loads(schema.sample_data)
        return None, None

class QuestionGenerationAgent:
    def __init__(self):
        self.model = "gpt-4"

    def generate_sql_prompt(self, schema, sample_data, difficulty, statements):
        allowed_statements = ', '.join(statements)

        # Customize the prompt based on the difficulty level and selected statements
        if "WHERE" in statements:
            if difficulty in ["Level 1", "Level 2"]:
                complexity_instruction = "Generate a basic SQL question using SELECT, FROM, and WHERE clauses with simple conditions."
            elif difficulty == "Level 3":
                complexity_instruction = "Generate a basic SQL question using SELECT, FROM, WHERE clauses with multiple conditions, including basic logical operators (AND, OR)."
            elif difficulty in ["Level 4", "Level 5"]:
                complexity_instruction = "Generate an SQL question using SELECT, FROM, WHERE, and advanced conditions like LIKE, IN, or BETWEEN."

        elif "JOIN" in statements:
            if difficulty in ["Level 1", "Level 2"]:
                complexity_instruction = "Generate a basic SQL question using SELECT, FROM, and JOIN to combine data from two tables."
            elif difficulty in ["Level 3", "Level 4"]:
                complexity_instruction = "Generate an SQL question using SELECT, FROM, JOIN with multiple tables and complex conditions."
            elif difficulty == "Level 5":
                complexity_instruction = "Generate a SQL question involving complex JOIN operations, and advanced filtering techniques using LIKE, BETWEEN or IN."

        elif "GROUP BY" in statements:
            if "HAVING" in statements:
                if difficulty in ["Level 1", "Level 2"]:
                    complexity_instruction = "Generate a basic SQL question using SELECT, FROM, GROUP BY with a simple HAVING clause."
                elif difficulty in ["Level 3", "Level 4"]:
                    complexity_instruction = "Generate an SQL question using SELECT, FROM, GROUP BY, and HAVING with more complex conditions."
                elif difficulty == "Level 5":
                    complexity_instruction = "Generate an advanced SQL question using SELECT, FROM, GROUP BY, and HAVING with multiple filtering conditions but without subqueries."
            else:
                if difficulty in ["Level 1", "Level 2"]:
                    complexity_instruction = "Generate a basic SQL question using SELECT, FROM, and GROUP BY with simple aggregation."
                elif difficulty in ["Level 3", "Level 4"]:
                    complexity_instruction = "Generate an SQL question using SELECT, FROM, and GROUP BY with more complex aggregation and filtering."
                elif difficulty == "Level 5":
                    complexity_instruction = "Generate an advanced SQL question using SELECT, FROM, and GROUP BY with complex conditions, possibly involving advanced filtering techniques."

        elif "ORDER BY" in statements:
            if difficulty in ["Level 1", "Level 2"]:
                complexity_instruction = "Generate a basic SQL question using SELECT, FROM, and ORDER BY with simple sorting."
            elif difficulty in ["Level 3", "Level 4"]:
                complexity_instruction = "Generate an SQL question using SELECT, FROM, and ORDER BY with multiple sorting criteria."
            elif difficulty == "Level 5":
                complexity_instruction = "Generate an advanced SQL question using SELECT, FROM, and ORDER BY with complex sorting criteria and advanced filtering techniques."

        prompt = (
            f"{complexity_instruction}\n\n"
            f"Here is the database schema:\n\n{schema}\n\n"
            f"Sample data for context:\n\n{json.dumps(sample_data, indent=4)}\n\n"
            f"The SQL should only include the following statements: {allowed_statements}.\n\n"
            "Respond with a JSON object with fields 'question' and 'solution'."
        )
        
        return prompt

    def get_response(self, prompt, num_responses=3):
        try:
            responses = []
            for _ in range(num_responses):
                response = openai.ChatCompletion.create(
                    model=self.model,
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

class ValidationAgent:
    def __init__(self):
        self.model = "gpt-4"

    def validate_sql(self, sql, allowed_statements):
        allowed_statements = [stmt.upper() for stmt in allowed_statements]
        sql_upper = sql.upper()
        unallowed_statements = ["JOIN", "ORDER BY", "GROUP BY", "HAVING", "SUBQUERY", "UNION"]
        
        for statement in unallowed_statements:
            if statement in sql_upper and statement not in allowed_statements:
                return False
        return self.validate_with_api(sql)

    def validate_with_api(self, sql):
        prompt = (
            f"Validate the following SQL query. Respond with 'Valid' if the query is valid, "
            f"otherwise respond with 'Invalid'. Query:\n\n{sql}"
        )
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an assistant skilled in SQL validation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50
            )
            validation_result = response['choices'][0]['message']['content'].strip().lower()
            return validation_result == 'valid'
        except Exception as e:
            st.error(f"Error during validation: {str(e)}")
            return False

    def validate_sample_data(self, schema, sample_data):
        return True

    def parse_response(self, response):
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
            parts = response.split('Solution:')
            if len(parts) == 2:
                question = parts[0].strip()
                solution = parts[1].strip()
                return question, solution
            return "Invalid response format", "Invalid response format"

class UIAgent:
    def __init__(self, schema_agent, question_agent, validation_agent):
        self.schema_agent = schema_agent
        self.question_agent = question_agent
        self.validation_agent = validation_agent

    def run(self):
        st.sidebar.title("SQL Question Generator😁")
        st.sidebar.write("Navigate through the pages to generate questions, view history, and manage schemas.")
        page = st.sidebar.radio("Choose a page", ["Home", "Generate Questions", "Questions History", "Saved Schemas"])

        if page == "Home":
            st.title("Welcome to the SQL Question Generator!😄")
            st.write("This application helps you generate SQL questions and solutions based on specific domains and difficulty levels.")

        elif page == "Generate Questions":
            self.generate_questions_page()

        elif page == "Questions History":
            self.questions_history_page()

        elif page == "Saved Schemas":
            self.saved_schemas_page()

        
    def generate_questions_page(self):
        st.title("Generate SQL Questions")
        session = Session()

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

        # Fetch the saved schemas using SchemaAgent
        saved_schemas = self.schema_agent.get_saved_schemas()
        saved_schema_names = [schema.name for schema in saved_schemas]
        
        if st.session_state.show_settings:
            col1, col2 = st.columns(2)
            with col1:
                schema_option = st.selectbox("Select a schema or input your own", saved_schema_names + ["Custom"])
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
                # Load the selected saved schema and its sample data
                schema, sample_data = self.schema_agent.get_schema_and_data(schema_option)
                

        if st.button("Show Schema and Data🗃️"):
            st.session_state.show_sample_data = True
            st.session_state.schema = schema

            # Explicitly assign the sample_data to session state
            st.session_state.sample_data = sample_data

            st.experimental_rerun()

        if st.session_state.show_sample_data:
            st.write("Sample Data:")

            # Display each table's data
            try:
                for table_name, data in st.session_state.sample_data.items():
                    st.write(f"**{table_name}**")
                    if data:
                        sample_data_df = pd.DataFrame(data)
                        st.table(sample_data_df)
                    else:
                        st.write("No data available for this table.")
            except ValueError as e:
                st.error(f"Error displaying sample data: {e}")

            if st.button("Hide Sample Data"):
                st.session_state.show_sample_data = False
                st.experimental_rerun()

        if st.button("Generate Questions🤖"):
            toggle_settings()
            if self.validation_agent.validate_sample_data(st.session_state.schema, st.session_state.sample_data):
                with st.spinner("Generating questions..."):
                    questions, solutions = self.generate_questions_with_retries(st.session_state.schema, st.session_state.sample_data, difficulty_level, sql_statements, num_questions, session)
                
                st.session_state.questions = questions
                st.session_state.solutions = solutions
                st.balloons()
            else:
                st.error("Sample data validation failed. Please check your sample data and try again.")

        # Display questions, solutions
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

            if st.button("Save and Download🗃️"):
                questions_content_md = "\n\n".join(
                    [f"### Question {i+1}:\n\n{edited_questions[i]}\n\n**Solution:**\n\n{edited_solutions[i]}" for i in range(len(edited_questions))]
                )
                questions_content_txt = "\n\n".join(
                    [f"Question {i+1}:\n\n{edited_questions[i]}\n\nSolution:\n\n{edited_solutions[i]}" for i in range(len(edited_questions))]
                )
                download_file(f"{filename}.md", questions_content_md)
                download_file(f"{filename}.txt", questions_content_txt)

            if st.button("Export to XML⬆️"):
                if 'questions' in st.session_state:
                    xml_content = self.export_to_xml(st.session_state.questions, st.session_state.solutions)
                    st.download_button(label="Download XML", data=xml_content, file_name=f"{filename}.xml")
                st.success("Exported questions to XML file successfully!")
                st.balloons()

            if st.button("Toggle Settings⚙️"):
                toggle_settings()


    
    def export_to_xml(self, questions, solutions):
        quiz = ET.Element('quiz')

        for i, (question, solution_set) in enumerate(zip(questions, solutions), 1):
            question_element = ET.SubElement(quiz, 'question', type="coderunner")

            name = ET.SubElement(question_element, 'name')
            text = ET.SubElement(name, 'text')
            text.text = f"Question {i}"

            questiontext = ET.SubElement(question_element, 'questiontext', format="html")
            text = ET.SubElement(questiontext, 'text')
            #text.text = f"<![CDATA[{escape_cdata(question)}]]>"
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
            cleaned_solution = solution_set.replace('```', '').strip()
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

    def generate_questions_with_retries(self, schema, sample_data, difficulty, statements, num, session, max_retries=3):
        questions = []
        solutions = []
        retries = 0

        while len(questions) < num and retries < max_retries:
            generated_questions, generated_solutions = self.generate_and_validate_questions(schema, sample_data, difficulty, statements, num - len(questions))
            
            for question, solution in zip(generated_questions, generated_solutions):
                if "valid" in question.lower():
                    retries += 1
                    break
                questions.append(question)
                solutions.append(solution)

        if retries == max_retries:
            questions.extend(["Error generating question. Please try again."] * (num - len(questions)))
            solutions.extend(["Error generating solution."] * (num - len(solutions)))

        for question_text, solution_text in zip(questions, solutions):
            new_question = Question(text=question_text, solution=solution_text)
            session.add(new_question)
        session.commit()

        return questions, solutions

    def generate_and_validate_questions(self, schema, sample_data, difficulty, statements, num):
        questions = []
        solutions = []
        for _ in range(num):
            prompt = self.question_agent.generate_sql_prompt(schema, sample_data, difficulty, statements)
            response = self.question_agent.get_response(prompt)
            
            for res in response:
                question_text, solution_text = self.validation_agent.parse_response(res)
                if self.validation_agent.validate_sql(solution_text, statements):
                    questions.append(question_text)
                    solutions.append(solution_text)
                    break
            else:
                questions.append("No valid question generated.")
                solutions.append("No valid solution available.")
        return questions, solutions

    def questions_history_page(self):
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

    def saved_schemas_page(self):
        st.title("Saved Schemas")
        session = Session()
        
        new_schema_name = st.text_input("Schema Name")
        new_schema_content = st.text_area("Schema SQL Commands")
        sample_data_input = st.text_area("Sample Data (as JSON)")
        
        if st.button("Save Schema"):
            if new_schema_name and new_schema_content and sample_data_input:
                try:
                    sample_data = json.loads(sample_data_input)
                    self.schema_agent.save_schema(new_schema_name, new_schema_content, json.dumps(sample_data))
                    st.success("Schema saved successfully!")
                except json.JSONDecodeError:
                    st.error("Invalid JSON format for sample data.")
            else:
                st.error("Please provide both name, schema content, and sample data.")

        saved_schemas = self.schema_agent.get_saved_schemas()
        for schema in saved_schemas:
            st.subheader(schema.name)
            st.code(schema.schema_sql)
            st.json(json.loads(schema.sample_data))
            st.button("Copy Schema", key=f"copy_{schema.id}", on_click=st.experimental_set_query_params, kwargs={"schema": schema.schema_sql})
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
    background-color: #ffffcc !important;
    font-size: 20px !important;
    color: #362624 !important;
}}
th, td {{
    border: 1px solid #FFA07A;  /* Set the border color to black */
    padding: 8px;
    color: #654321;  /* Dark Brown text color for good readability */
}}

th {{
    background-color: #FFDAB9  ;
   
}}
# tr:nth-child(even) {{
#     background-color: #FFF5EE;  /* Very light orange (Seashell) background for even rows */
# }}
tr:hover {{
    background-color: #FFE4B5;

}}
table {{
    border-collapse: collapse;  /* Ensures that the table borders are merged together */
    border: 3px solid black;    /* Adds a thicker black border around the entire table */
    margin: 10px 0;             /* Adds some margin between tables to separate them */
    box-shadow: 0px 0px 0px 3px black;
    }}

</style>
"""

# Apply the CSS style
st.markdown(page_bg_img, unsafe_allow_html=True)

# Initialize session and agents
session = Session()
schema_agent = SchemaAgent(session)
question_agent = QuestionGenerationAgent()
validation_agent = ValidationAgent()
ui_agent = UIAgent(schema_agent, question_agent, validation_agent)

# Run the UI
ui_agent.run()
