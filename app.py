from openai import OpenAI
import sqlite3
import schedule
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build


from dotenv import load_dotenv

load_dotenv()


print(os.getenv("OPENAI_API_KEY"))

# OpenAI client setup with API key directly included
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Path to your Google service account JSON key

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=credentials)
CALENDAR_ID = 'd1f1f9507ffefdcacb64c9cf194b57ed20450b2fff09eba084552ce184e6ba9f@group.calendar.google.com'  # Or use your calendar ID

# Flask setup
app = Flask(__name__)

# Database setup
conn = sqlite3.connect('tasks.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                deadline TEXT,
                priority TEXT,
                duration INTEGER,
                calendar_event_id TEXT,
                notified INTEGER DEFAULT 0)''')
conn.commit()

def extract_task_details(user_input):
    prompt = f"""
    Extract the task name, deadline and convert it in YYYY-MM-DD HH:MM format, priority (High/Medium/Low), 
    and estimated time in minutes from this input:

    "{user_input}"

    Respond in JSON format with keys: name, deadline, priority, duration as a number.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful task assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content.strip()
        print("OpenAI raw response:", content)
        return json.loads(content)
    except json.JSONDecodeError:
        print("Failed to decode OpenAI response as JSON.")
        raise
    except Exception as e:
        print("OpenAI API call failed:", e)
        raise

def add_task_to_db(task):
    event_id = add_task_to_calendar(task)
    c.execute("INSERT INTO tasks (name, deadline, priority, duration, calendar_event_id) VALUES (?, ?, ?, ?, ?)",
              (task['name'], task['deadline'], task['priority'], task['duration'], event_id))
    conn.commit()

def add_task_to_calendar(task):
    try:
        start_time = datetime.strptime(task['deadline'], "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(minutes=task['duration'])
        event = {
            'summary': task['name'],
            'description': f"Priority: {task['priority']}, Duration: {task['duration']} minutes",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'visibility': 'default'
        }
        created_event = calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print("Event created:", created_event.get('htmlLink'))
        return created_event.get('id')
    except Exception as e:
        print("Failed to add task to Google Calendar:", e)
        return None

def get_all_tasks():
    c.execute("SELECT id, name, deadline, priority, duration FROM tasks")
    return c.fetchall()

def delete_task(task_id):
    c.execute("SELECT calendar_event_id FROM tasks WHERE id = ?", (task_id,))
    result = c.fetchone()
    if result and result[0]:
        try:
            calendar_service.events().delete(calendarId=CALENDAR_ID, eventId=result[0]).execute()
            print("Event deleted from Google Calendar")
        except Exception as e:
            print("Failed to delete event from Google Calendar:", e)
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

def send_reminder(task):
    print(f"[Reminder] Task: {task[1]} is due at {task[2]}!")
    c.execute("UPDATE tasks SET notified = 1 WHERE id = ?", (task[0],))
    conn.commit()

def check_due_tasks():
    now = datetime.now()
    c.execute("SELECT id, name, deadline FROM tasks WHERE notified = 0")
    tasks = c.fetchall()
    for task in tasks:
        deadline = datetime.strptime(task[2], "%Y-%m-%d %H:%M")
        if now >= deadline - timedelta(minutes=15):
            send_reminder(task)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form['prompt']
        task = extract_task_details(user_input)
        add_task_to_db(task)
        return redirect(url_for('index'))
    tasks = get_all_tasks()
    return render_template('index.html', tasks=tasks)

@app.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    delete_task(task_id)
    return redirect(url_for('index'))
    
    
def delete_google_calendar_event(event_id):
    try:
        if event_id:
            calendar_service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
            print(f"Deleted Google Calendar event {event_id}")
    except Exception as e:
        print("Failed to delete calendar event:", e)

@app.route('/api/task', methods=['POST'])
def create_task_api():
    data = request.json
    user_input = data.get('task')
    task_details = extract_task_details(user_input)
    add_task_to_db(task_details)
    return jsonify({"message": "Task added successfully.", "task": task_details})

@app.route('/api/tasks', methods=['GET'])
def list_tasks_api():
    tasks = get_all_tasks()
    return jsonify(tasks)

if __name__ == '__main__':
    schedule.every(1).minutes.do(check_due_tasks)

    from threading import Thread
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    Thread(target=run_scheduler, daemon=True).start()

    os.makedirs("templates", exist_ok=True)
    with open("templates/index.html", "w") as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Task Scheduler</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; }
        h1 { color: #333; }
        form { margin-bottom: 20px; background: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        textarea { width: 100%; padding: 10px; margin-bottom: 10px; height: 100px; }
        button { padding: 10px 15px; background-color: #28a745; color: white; border: none; cursor: pointer; margin-top: 10px; }
        button.delete { background-color: #dc3545; margin-left: 10px; }
        ul { list-style-type: none; padding: 0; }
        li { background-color: white; margin-bottom: 10px; padding: 15px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <h1>AI Task Scheduler</h1>
    <form method="POST">
        <label>Enter your task details:</label>
        <textarea name="prompt" placeholder="e.g. Schedule a meeting with John on 07/04/2025 at 10 AM, priority high, 30 minutes"></textarea>
        <button type="submit">Add Task</button>
    </form>

    <h2>Your Tasks</h2>
    <ul>
        {% for task in tasks %}
        <li>
            <strong>{{ task[1] }}</strong><br>
            <small>Due: {{ task[2] }}</small><br>
            <small>Priority: {{ task[3] }} | Duration: {{ task[4] }} min</small>
            <form action="/delete/{{ task[0] }}" method="POST" style="display:inline;">
                <button class="delete" type="submit">Delete</button>
            </form>
        </li>
        {% endfor %}
    </ul>
</body>
</html>
''')

    app.run(debug=True,port=5001)