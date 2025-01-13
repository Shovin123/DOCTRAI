@app.route('/upload', methods=['POST'])
def upload():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    # Extract form data
    name = request.form.get('name')
    age = request.form.get('age')
    gender = request.form.get('gender')

    if not name or not age or not gender:
        return jsonify({"error": "Missing patient details"}), 400

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
        final_summary = summarized_conversation(mapped_output)

        # Step 4: Generate the PDF report
        report_pdf_path = generate_reportpdf(name, age, gender, final_summary)

        # Return the generated PDF back to the user
        return send_file(report_pdf_path, as_attachment=True, download_name="patient_report.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
