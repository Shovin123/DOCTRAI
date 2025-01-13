from flask import Flask, render_template, request, redirect, send_file, url_for, flash, session, send_from_directory
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId
import os
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import torch
from openai import OpenAI
from flask import jsonify
from datetime import datetime

csv_file = r'C:\Users\srini\OneDrive\Desktop\testing-final\all_symptoms.csv'  # Replace with your actual file path
# Set the folder containing your PDFs (project root directory)
PDF_FOLDER = os.getcwd()  # Current working directory

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set your secret key (or use an environment variable)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB URI
db = client['user_db']  # Database name
users_collection = db['users']  # Collection for storing user data

@app.route('/')
def index():
    return render_template('login.html')

@app.route("/pdf_table")
def pdf_table():
    # Get all PDF files in the root directory
    files = [
        {
            "name": f,
            "date": datetime.fromtimestamp(os.path.getmtime(os.path.join(PDF_FOLDER, f))).strftime('%Y-%m-%d %H:%M:%S'),
            "url": url_for('serve_pdf', filename=f)
        }
        for f in os.listdir(PDF_FOLDER)
        if f.endswith(".pdf")
    ]
    return render_template("pdf_table.html", files=files)

@app.route("/pdfs/<path:filename>")
def serve_pdf(filename):
    # Serve the PDF from the root directory
    return send_from_directory(PDF_FOLDER, filename)

@app.route('/record')
def record():
    return render_template('record.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle form submission
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone_number = request.form.get('phone_number')
        age = request.form.get('age')
        photo = request.files.get('photo')

        # Save the photo
        if photo:
            photo_filename = f"{username}_{photo.filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            photo.save(photo_path)
        else:
            photo_filename = None

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Check if the email or username already exists
        if users_collection.find_one({'email': email}):
            flash('Email is already registered!', 'error')
            return redirect(url_for('signup'))
        
        if users_collection.find_one({'username': username}):
            flash('Username is already taken!', 'error')
            return redirect(url_for('signup'))

        # Insert the new user into the database
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,  # Store the hashed password
            'phone_number': phone_number,
            'age': int(age),
            'photo': photo_filename
        }
        users_collection.insert_one(user_data)
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))  # Redirect to the login page

    # Handle GET request: Render the signup page
    return render_template('signup.html')


@app.route('/signup_hosp', methods=['POST','GET'])
def signup_hosp():
    # Get form data
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        hospital_name = request.form.get('hosp_name')

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('index'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Check if the email or username already exists
        if users_collection.find_one({'email': email}):
            flash('Email is already registered!', 'error')
            return redirect(url_for('index'))
        
        if users_collection.find_one({'username': username}):
            flash('Username is already taken!', 'error')
            return redirect(url_for('index'))

        # Insert the new user into the database
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'hospital_name': hospital_name
        }
        users_collection.insert_one(user_data)
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('index'))
    return render_template('signup_hosp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Find the user by email
        user = users_collection.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):  # Check if the password is correct
            session['user_id'] = str(user['_id'])  # Store user ID in session
            session['username'] = user['username']  # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('profile'))  # Redirect to dashboard/home page
        else:
            flash('Invalid email or password!', 'error')
    return render_template('login.html')



@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in
    if 'user_id' in session:
        return f'Welcome {session["username"]}! <br> <a href="/logout">Logout</a> <br> <a href="/profile">View Profile</a>'
    else:
        return redirect(url_for('login'))


@app.route('/profile')
def profile():
    if 'user_id' in session:
        try:
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            if user:
                return render_template(
                    'profile.html',
                    username=user.get('username'),
                    email=user.get('email'),
                    phone_number=user.get('phone_number'),
                    age=user.get('age'),
                    photo=user.get('photo')
                )
            else:
                flash('User not found', 'error')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('An error occurred while fetching profile details.', 'error')
            print(f"Error: {e}")
            return redirect(url_for('dashboard'))
    else:
        flash('You need to log in first!', 'error')
        return redirect(url_for('login'))


@app.route('/main')
def main():
    # Check if the user is logged in
    if 'user_id' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, audio_file.filename)
    audio_file.save(filepath)

    # Process the uploaded audio file
    try:
        # Step 1: Transcribe the audio file
        transcription = transcribe_audio(filepath)

        # Step 2: Speaker map the transcription
        mapped_output = speaker_map_transcription(transcription)
        
        # Step 3: Summarize the mapped transcription
        final_summary = summarized_conversation(mapped_output) + extract_and_map_symptoms(mapped_output, csv_file)

        # Step 4: Generate the PDF report
        report_pdf_path = generate_reportpdf("Prem Je Kalister", 25, "Male", final_summary)

        # Return the generated PDF back to the user
        return send_file(report_pdf_path, as_attachment=True, download_name="patient_report.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def transcribe_audio(audio_file_path):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3-turbo"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, 
        torch_dtype=torch_dtype, 
        low_cpu_mem_usage=True, 
        use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )

    result = pipe(audio_file_path, return_timestamps=True)
    transcription = result["text"]
    
    return transcription

def speaker_map_transcription(transcription):
    client = OpenAI()

    instruction = f"""The below is the transcript of a conversation between a doctor and a patient, and the dialogues are not speaker mapped.
        You are instructed to read the whole conversation and identify the speaker's dialogues and label the dialogues as "Doctor:" and "Patient".
        Transcript:{transcription}
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": instruction
        }],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    output = response.choices[0].message.content
    return output

import pandas as pd
from openai import OpenAI
from rapidfuzz import process

def extract_and_map_symptoms(output, csv_file):
    """
    Extract and map symptoms from a paragraph based on a list of known symptoms from a CSV file.

    Parameters:
    paragraph (str): The input text containing potential symptoms.
    csv_file (str): Path to the CSV file containing known symptoms.
    api_key (str): OpenAI API key.

    Returns:
    str: Mapped symptoms as a comma-separated string.
    """
    # Initialize OpenAI API
    #openai.api_key = api_key

    # Load symptoms from the CSV file
    def load_symptoms(csv_file):
        df = pd.read_csv(csv_file, encoding='latin-1')
        return list(df['Symptoms'].dropna().unique())

    # Normalize symptom strings
    def normalize_symptoms(symptoms):
        return [symptom.lower().strip() for symptom in symptoms]

    # Split grouped symptoms into individual ones
    def split_combined_symptoms(extracted_symptoms):
        split_symptoms = []
        for symptom in extracted_symptoms:
            # Split by common delimiters like newlines, commas, or dashes
            if '\n' in symptom or '-' in symptom or ',' in symptom:
                split_symptoms.extend(symptom.replace('-', '').replace('\n', ',').split(','))
            else:
                split_symptoms.append(symptom)
        return [sym.strip() for sym in split_symptoms if sym.strip()]  # Clean and remove empty strings

    # Map extracted symptoms to known symptoms using fuzzy matching
    def map_to_known_symptoms(extracted_symptoms, known_symptoms):
        mapped_symptoms = []
        for symptom in extracted_symptoms:
            # Find the best match from known symptoms
            best_match, score, _ = process.extractOne(symptom, known_symptoms)
            if score > 80:  # Only consider matches with a high similarity score
                mapped_symptoms.append(best_match)
        return mapped_symptoms

    # Load known symptoms
    known_symptoms = load_symptoms(csv_file)
    
    #paragraph=speaker_map_transcription(transcription)

    # Extract symptoms using OpenAI API
    prompt = f"Extract symptoms mentioned in the following text:\n\n{output}\n\nSymptoms:"
    client=OpenAI()
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.3
    )

    # Split response into individual symptoms
    extracted_symptoms = response.choices[0].message.content.strip().split(', ')
    extracted_symptoms = split_combined_symptoms(extracted_symptoms)  # Preprocess extracted symptoms
    normalized_extracted = normalize_symptoms(extracted_symptoms)
    normalized_known_symptoms = normalize_symptoms(known_symptoms)

    # Map extracted symptoms to standardized terms
    mapped_symptoms = map_to_known_symptoms(normalized_extracted, normalized_known_symptoms)

    # Return the mapped symptoms as a comma-separated string
    #return ", ".join(mapped_symptoms)
    string_symp= ", ".join(mapped_symptoms)
    symps=string_symp
    return symps

def summarized_conversation(mapped_output):
    client = OpenAI()

    instruction = f"""You are an Indian General Doctor , The below is the transcript of a conversation between a doctor and a patient, summarize the conversation . 
    Transcript:{mapped_output} , identify the symptoms present in the conversation , give the exact summarization of the conversation in the form of doctor's notes 
    and recommend medicines for the symptoms and generate a medical prescription with the name and brand of the general medicine along with dosage instructions and precautions.

    Example Output:

    Summary: Paste the conversation summary here

    Symptoms: Sore throat, fatigue, mild cough, slight fever (100 degrees)

    Possible Disease: Upper respiratory tract infection or viral infection
    
    Prescription:
    - Rest and hydration
    - Over-the-counter medications (acetaminophen, throat lozenges, cough syrup)
    - Consider throat swab for strep throat if indicated
    
    Dosage Instructions:
    - Acetaminophen (Brand: Tylenol): Take 500mg every 4-6 hours as needed for fever
    - Throat lozenges/sprays: Use as directed on packaging for sore throat
    - Cough syrup (Brand: Robitussin): Take 10ml every 4-6 hours as needed for cough
    
    Precautions:
    - Get plenty of rest
    - Stay hydrated
    - Avoid contact with sick individuals
    - Follow up if symptoms worsen or persist in the next few days
    
    Please consult with a healthcare professional before starting any new medications.

    The above example is the structure of the output you need to provide.
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": instruction
        }],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    output_summary = response.choices[0].message.content
    return output_summary


"""def generate_reportpdf(patient_name, age, gender, final_summary, file_name="patient_report.pdf"):
    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2.0, height - 100, "Shovin Hospitals")

    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.line(50, height - 110, width - 50, height - 110)

    c.setFont("Helvetica", 14)

    c.drawString(50, height - 150, "Name: ")
    c.drawString(150, height - 150, patient_name)

    c.drawString(50, height - 180, "Age: ")
    c.drawString(150, height - 180, str(age))

    c.drawString(50, height - 210, "Gender: ")
    c.drawString(150, height - 210, gender)

    c.setLineWidth(1)
    c.line(50, height - 220, width - 50, height - 220)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 250, "Patient Report:")

    c.setFont("Helvetica", 12)
    text_object = c.beginText(50, height - 280)
    text_object.setTextOrigin(50, height - 280)
    text_object.setLeading(14)
    text_object.textLines(final_summary)

    c.drawText(text_object)
    c.save()

    return file_name"""

from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet

def generate_reportpdf(patient_name, age, gender, final_summary, file_name="patient_report.pdf"):
    # Create a PDF document template
    pdf = SimpleDocTemplate(file_name, pagesize=A4)
    width, height = A4

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']

    # Create content
    elements = []

    # Add hospital name as the title
    elements.append(Paragraph("Shovin Hospitals", title_style))

    # Add patient details
    patient_details = f"<b>Name:</b> {patient_name}<br/><b>Age:</b> {age}<br/><b>Gender:</b> {gender}"
    elements.append(Paragraph(patient_details, normal_style))

    # Add a separator line
    elements.append(Paragraph("<br/>", normal_style))

    # Add the "Patient Report" heading
    elements.append(Paragraph("<b>Patient Report:</b>", title_style))

    # Add the summarized conversation
    elements.append(Paragraph(final_summary.replace("\n", "<br/>"), normal_style))

    # Build the PDF
    pdf.build(elements)

    return file_name



if __name__ == '__main__':
    app.run(debug=True)