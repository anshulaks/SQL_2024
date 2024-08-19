import streamlit as st
import openai
from secret_key import openai_key

# Set OpenAI API key
openai.api_key = openai_key

def generate_template(schema, sample_data, base_template):
    prompt = (
        f"Generate a Moodle-compatible template using the following schema and sample data:\n\n"
        f"Schema:\n{schema}\n\n"
        f"Sample Data:\n{sample_data}\n\n"
        f"Base Template:\n{base_template}\n\n"
        "Format the output as a complete Python script."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Or your chosen model
            messages=[
                {"role": "system", "content": "You are an assistant skilled in Python template generation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        generated_template = response.choices[0].message['content']
        return generated_template
    except Exception as e:
        st.error(f"Error generating template: {str(e)}")
        return None

def template_generator_page():
    st.title("Template Generator")
    
    base_template = st.text_area("Base Template", height=300)
    schema = st.text_area("Schema", height=200)
    sample_data = st.text_area("Sample Data (JSON format)", height=200)
    
    if st.button("Generate Template"):
        if not base_template or not schema or not sample_data:
            st.error("Please provide all inputs: Base Template, Schema, and Sample Data.")
        else:
            template = generate_template(schema, sample_data, base_template)
            if template:
                st.code(template, language="python")
                st.download_button("Download Generated Template", data=template, file_name="generated_template.py")
