import streamlit as st
from openai import OpenAI
from pypdf2 import PdfReader
import docx2txt
import tempfile
from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Display the banner image
st.image("imagebanner.png", use_column_width=False)

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = ""


# Function to extract text from PDF
def extract_text_from_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


# Function to extract text from DOCX
def extract_text_from_docx(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
        temp_file.write(file.read())
        temp_file_path = temp_file.name
    text = docx2txt.process(temp_file_path)
    return text


# Function to handle file upload and text extraction
def handle_file(uploaded_files):
    extracted_text = ""
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            extracted_text += extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text += extract_text_from_docx(uploaded_file)
        elif uploaded_file.type == "text/plain":
            extracted_text += str(uploaded_file.read(), "utf-8")
    return extracted_text


# Function to summarize text if it's too long
def summarize_text(text, max_length=500):
    if len(text) > max_length:
        summary_prompt = f"Summarize the following text to be under {max_length} characters:\n{text}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = response.choices[0].message.content
        return summary
    else:
        return text


# Sidebar for file uploads and extracted text display
st.sidebar.header("Upload Files")
uploaded_files = st.sidebar.file_uploader("Choose files", accept_multiple_files=True, type=['pdf', 'docx', 'txt'])

extracted_text = handle_file(uploaded_files) if uploaded_files else ""
clear_button = st.sidebar.button("Clear Extracted Text")

if clear_button:
    extracted_text = ""

st.sidebar.text_area("Extracted Text", extracted_text, height=200)

# Tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Conversational Brand Expert", "Scoring Tab", "Generate Image"])

with tab1:
    st.header("Conversational Brand Expert")
    user_prompt = st.text_input("User Prompt")
    chat_history = st.session_state["chat_history"]
    if st.button("Generate Response"):
        # Include extracted text in the system message
        system_message = f"You are a helpful assistant. Here is the text from the uploaded documents: {extracted_text}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
        )
        assistant_response = response.choices[0].message.content
        chat_history += f"User: {user_prompt}\nAI: {assistant_response}\n\n"
        st.session_state["chat_history"] = chat_history
    st.text_area("Chat History", chat_history, height=200, key="chat_history")

with tab2:
    st.header("Scoring Tab")

    if st.button("Score Text"):
        scoring_prompt = (
                "Score the following text based on the provided brand voice guidelines. "
                "Give a score from 1 to 10 for each parameter: Clarity, Consistency, Tone, Personality, Point of View.\n" + extracted_text
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": scoring_prompt}
            ]
        )
        scores = response.choices[0].message.content.split("\n")
        scores_dict = {param.split(":")[0].strip(): param.split(":")[1].strip() for param in scores if ":" in param}

        # Display scores in a table
        st.write("## Scores Table")
        st.table(scores_dict)

        # Calculate and display overall score
        numeric_scores = [float(score) for score in scores_dict.values() if score.strip().isdigit()]
        if numeric_scores:
            overall_score = sum(numeric_scores) / len(numeric_scores)
            st.write(f"## Overall Score: {overall_score}")

        # Display explanations
        st.write("## Explanations")
        for param, score in scores_dict.items():
            explanation_prompt = f"Explain the score for {param} based on the provided brand voice guidelines and the text:\n{extracted_text}"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": explanation_prompt}
                ]
            )
            explanation = response.choices[0].message.content
            st.write(f"### {param} Explanation")
            st.write(explanation)

with tab3:
    st.header("Generate Brand Image")
    image_prompt = st.text_input("Enter image generation prompt:", key='image_prompt')
    if st.button("Generate Image"):
        if extracted_text:
            summarized_text = summarize_text(extracted_text)
            combined_prompt = f"Based on the following extracted text, {summarized_text}, generate an image: {image_prompt}"
        else:
            combined_prompt = image_prompt

        response = client.images.generate(
            model="dall-e-3",
            prompt=combined_prompt,
            size="1024x1024",
            n=1
        )
        image_url = response.data[0].url
        st.image(image_url, caption="Generated Image")
