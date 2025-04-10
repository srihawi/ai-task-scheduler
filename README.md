# 🧠 AI Task Scheduler

**AI Task Scheduler** is a personal productivity web application that allows users to schedule and manage tasks using natural language. The app leverages OpenAI's GPT model to extract structured task information from free-text input and automatically adds these tasks to a local database and Google Calendar.

---

## 💡 Key Features

- **Natural Language Input**: Enter tasks like "Submit the report by Friday at 2 PM, high priority, 45 minutes" and the app understands and schedules them.
- **Google Calendar Integration**: Each task is added as a calendar event, including title, time, and description.
- **Reminders**: The app checks tasks every minute and alerts the user if any are due within 15 minutes.
- **Web-Based Interface**: Users interact through a simple, clean Flask-powered web UI.
- **Task Management**: Tasks are stored in an SQLite database with options to view and delete them.

---

## 🔧 Technologies Used

- Python + Flask (backend & server)
- OpenAI API (language understanding)
- Google Calendar API (event scheduling)
- SQLite (lightweight task storage)
- HTML + Jinja2 (templating for the web interface)

---

## 🛠 Project Purpose

The purpose of this project is to demonstrate how language models can enhance productivity tools by transforming natural language into structured, actionable data. It also shows how to combine AI with APIs like Google Calendar to automate real-life workflows.

