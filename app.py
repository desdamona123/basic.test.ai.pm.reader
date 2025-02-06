from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Load user data from JSON
def load_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"students": []}

# Save user data to JSON
def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, indent=2, fp=f)

# Story generation function
def generate_story(pm_level, focus_words, theme, word_count):
    API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
    API_KEY = os.getenv('DEEPINFRA_TOKEN')  # Set this in your environment
    
    prompt = (
        f"Write a {word_count}-word story for a Level {pm_level} reader "
        f"using these words: {', '.join(focus_words)}. "
        f"Use theme: {theme}. Include a title at the start. "
        f"Strictly follow PM Level {pm_level} vocabulary and grammar."
    )

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return "Error generating story. Please try again."

# Routes
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/dashboard', methods=['POST'])
def dashboard():
    student_name = request.form['username'].strip()
    data = load_data()
    
    # Find or create student
    student = next((s for s in data['students'] if s['name'] == student_name), None)
    if not student:
        student = {
            "name": student_name,
            "pm_level": 5,  # Default level, update in JSON manually
            "focus_words": ["happy", "friend", "school"],  # Default words
            "stories": []
        }
        data['students'].append(student)
        save_data(data)
    
    session['student_name'] = student_name
    return render_template('dashboard.html', student=student)

@app.route('/create_story', methods=['POST'])
def create_story():
    data = load_data()
    student = next(s for s in data['students'] if s['name'] == session['student_name'])
    
    # Generate story
    story_content = generate_story(
        pm_level=student['pm_level'],
        focus_words=student['focus_words'],
        theme=request.form['theme'],
        word_count=int(request.form['word_count'])
    )
    
    # Store story
    new_story = {
        "title": story_content.split('\n')[0].replace('Title: ', ''),
        "content": story_content,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # Maintain max 10 stories
    student['stories'].append(new_story)
    if len(student['stories']) > 10:
        student['stories'] = student['stories'][-10:]
    save_data(data)
    
    return redirect(url_for('view_story', story_id=len(student['stories'])-1))

@app.route('/story/<int:story_id>')
def view_story(story_id):
    data = load_data()
    student = next(s for s in data['students'] if s['name'] == session['student_name'])
    return render_template('story.html', story=student['stories'][story_id])

@app.route('/logout')
def logout():
    session.pop('student_name', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)