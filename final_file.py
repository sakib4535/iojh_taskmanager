import streamlit as st
import sqlite3
from datetime import date, timedelta
import pandas as pd
from docx import Document

# List of employees and their roles (departments)
employees_data = [
    ("Zaedul Islam", "IT manager"),
    ("Ehsan", "Researcher"),
    ("Rakib", "Finance and Research"),
    ("Baki Billah", "Research"),
    ("Dilruba", "Marketing"),
    ("Hasnain", "Statistician"),
    ("Tanzila", "Customer Support"),
    ("Thrina", "Research Supervisor"),
    ("Faysal", "IT & Operations"),
    ("Suraiya", "HR"),
]



def init_db():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    # Create employees table
    cursor.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL
    )""")

    # Create tasks table
    cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        status TEXT DEFAULT 'Pending',
        assigned_to INTEGER,
        deadline DATE,
        priority TEXT,
        recurrence TEXT DEFAULT 'None',
        file_path TEXT,
        FOREIGN KEY (assigned_to) REFERENCES employees (id)
    )""")



    # Create subtasks table
    cursor.execute("""CREATE TABLE IF NOT EXISTS subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )""")

    # Checking if the recurrence column exists, and adding it if not
    try:
        cursor.execute("SELECT recurrence FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        # Add the recurrence column if it does not exist
        cursor.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT 'None'")

    # Populate employees table if empty
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        for name, department in employees_data:
            cursor.execute("INSERT INTO employees (name, department) VALUES (?, ?)", (name, department))

    connection.commit()
    connection.close()

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Email function
def send_email(subject, body, to_email):
    from_email = "your-email@gmail.com"  # Your email address
    password = "your-email-password"  # Your email password

    # Set up the MIME
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Set up the server and send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False



# Fetch all employees
def fetch_all_employees():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM employees")
    employees = cursor.fetchall()
    connection.close()
    return employees


def add_task(title, description, category, assigned_to, deadline, priority, recurrence, subtasks=[], file_path=None):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    # Insert the main task
    cursor.execute("""
    INSERT INTO tasks (title, description, category, status, assigned_to, deadline, priority, recurrence, file_path)
    VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?, ?)""",
                   (title, description, category, assigned_to, deadline, priority, recurrence, file_path))

    # Fetch the newly created task ID
    task_id = cursor.lastrowid

    # Insert any subtasks
    for subtask_title in subtasks:
        cursor.execute("INSERT INTO subtasks (task_id, title) VALUES (?, ?)", (task_id, subtask_title))

    connection.commit()
    connection.close()



# Fetch tasks assigned to an employee
def fetch_employee_tasks(employee_id, sort_by_priority=False):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    query = "SELECT * FROM tasks WHERE assigned_to = ?"

    if sort_by_priority:
        query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"

    cursor.execute(query, (employee_id,))
    tasks = cursor.fetchall()
    connection.close()
    return tasks


# Parse uploaded files
def parse_file(uploaded_file):
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        return df.to_string(), uploaded_file.name
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        content = "\n".join([para.text for para in doc.paragraphs])
        return content, uploaded_file.name
    else:
        return "Unsupported file format.", None


# Function to calculate remaining days
def get_remaining_days(deadline):
    now = date.today()
    deadline_date = pd.to_datetime(deadline).date()
    return (deadline_date - now).days


# Function to display status bulb
def status_bulb(status, remaining_time):
    if status == "Completed":
        return "🟢", "green"
    elif remaining_time <= 0:
        return "🔴", "red"
    elif remaining_time <= 2:
        return "🟡", "yellow"
    else:
        return "🟢", "green"


# Handle recurring tasks
def handle_recurring_tasks():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    # Get tasks with recurrence
    cursor.execute(
        "SELECT id, title, recurrence, deadline FROM tasks WHERE recurrence IS NOT NULL AND recurrence != 'None'")
    recurring_tasks = cursor.fetchall()

    for task in recurring_tasks:
        task_id, title, recurrence, deadline = task
        deadline_date = pd.to_datetime(deadline).date()
        now = date.today()

        if deadline_date < now:
            if recurrence == "Daily":
                new_deadline = deadline_date + timedelta(days=1)
            elif recurrence == "Weekly":
                new_deadline = deadline_date + timedelta(weeks=1)
            elif recurrence == "Monthly":
                new_deadline = deadline_date + pd.DateOffset(months=1)
            else:
                continue

            cursor.execute("""
            INSERT INTO tasks (title, description, category, assigned_to, deadline, priority, recurrence)
            SELECT title, description, category, assigned_to, ?, priority, recurrence FROM tasks WHERE id = ?""",
                           (new_deadline, task_id))

    connection.commit()
    connection.close()


# Initialize the database
init_db()


# Initialize Streamlit app
st.set_page_config(page_title="Task Management App", layout="wide")
st.title("Automated Task Management App - IOJH")

# Handle recurring tasks at app startup
handle_recurring_tasks()

# Sidebar for navigation
with st.sidebar:
    st.header("Navigation")

    if st.button("Employees Dashboard"):
        st.header("👨‍💼 Employees Dashboard")
        employees = fetch_all_employees()
        if employees:
            for emp_id, name in employees:
                st.markdown(f"**Name:** {name}")
        else:
            st.write("No employees found in the database.")

    # Add Task Section
    st.subheader("➕ Assign a Task")
    all_employees = fetch_all_employees()
    employee_names = {str(emp[0]): emp[1] for emp in all_employees}

    if employee_names:
        selected_emp_id = st.selectbox("Select Employee", options=employee_names.keys(),
                                       format_func=lambda emp_id: employee_names[emp_id])
        task_title = st.text_input("Task Title")
        task_description = st.text_area("Task Description")
        task_category = st.text_input("Category")
        task_priority = st.selectbox("Priority", options=["Low", "Medium", "High"])
        task_recurrence = st.selectbox("Recurrence", options=["None", "Daily", "Weekly", "Monthly"])
        task_deadline = st.date_input("Deadline", min_value=date.today())
        add_subtasks = st.checkbox("Add Subtasks?")

        subtasks = []
        if add_subtasks:
            num_subtasks = st.number_input("Number of Subtasks", min_value=1, value=1, step=1)
            for i in range(num_subtasks):
                subtasks.append(st.text_input(f"Subtask {i + 1} Title"))

        uploaded_file = st.file_uploader("Upload Supporting File (CSV or DOCX)", type=["csv", "docx"])
        file_name = None
        if uploaded_file:
            parsed_content, file_name = parse_file(uploaded_file)
            st.write("Preview of Uploaded File:")
            st.text(parsed_content)

        if st.button("Add Task"):
            if task_title:
                add_task(task_title, task_description, task_category, selected_emp_id, task_deadline, task_priority,
                         task_recurrence, subtasks, file_name)
                st.success(f"Task '{task_title}' assigned to {employee_names[selected_emp_id]}")
            else:
                st.error("Task Title is required!")

    else:
        st.write("No employees available for task assignment.")


#######################################


# Main Area - Tabs
tab1, tab2, tab3 = st.tabs(["📋 View Tasks", "📊 Visualizations", "🔧 Task Management"])

# Tab 1: View Tasks
with tab1:
    st.subheader("📋 All Tasks")
    sort_by_priority = st.checkbox("Sort by Priority")
    selected_emp_id = st.selectbox("View Tasks For", options=employee_names.keys(),
                                   format_func=lambda emp_id: employee_names[emp_id])

    tasks = fetch_employee_tasks(selected_emp_id, sort_by_priority)
    if tasks:
        for task in tasks:

            task_id, title, description, category, status, assigned_to, deadline, priority, recurrence, file_path = task + tuple([None] * (10 - len(task)))

            remaining_days = get_remaining_days(deadline)
            st.markdown(f"### {title} (ID: {task_id})")
            st.markdown(f"**Priority:** {priority} | **Recurrence:** {recurrence}")
            st.markdown(f"**Deadline:** {deadline} | **Remaining Days:** {remaining_days}")
            bulb, color = status_bulb(status, remaining_days)
            st.markdown(f"<div style='color:{color};'><b>{bulb} {status}</b></div>", unsafe_allow_html=True)
            st.markdown(f"**Category:** {category}")
            if file_path:
                st.markdown(f"**Uploaded File:** {file_path}")

            # Display Subtasks
            st.markdown("**Subtasks:**")
            connection = sqlite3.connect("tasks.db")
            cursor = connection.cursor()
            cursor.execute("SELECT title, status FROM subtasks WHERE task_id = ?", (task_id,))
            subtasks = cursor.fetchall()
            connection.close()
            for subtask in subtasks:
                sub_title, sub_status = subtask
                st.markdown(f"- {sub_title} ({sub_status})")

            st.divider()
    else:
        st.write("No tasks assigned to this employee.")

# Tab 2: Visualizations
import matplotlib.pyplot as plt

# Tab 2: Visualizations
import matplotlib.pyplot as plt

# Tab 2: Visualizations
with tab2:
    st.subheader("📊 Task Status Distribution")

    # Task status count visualization
    # Query to count tasks per employee
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    # Get count of tasks for each employee
    cursor.execute("""
        SELECT employees.name, COUNT(tasks.id) 
        FROM employees 
        LEFT JOIN tasks ON tasks.assigned_to = employees.id 
        GROUP BY employees.id
    """)
    task_count_data = cursor.fetchall()
    connection.close()

    # Separate the data into two lists: names and task counts
    employee_names_list = [data[0] for data in task_count_data]
    task_counts = [data[1] for data in task_count_data]

    # Plotting the data using Matplotlib
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(employee_names_list, task_counts, color='skyblue')
    ax.set_xlabel('Total Tasks Assigned')
    ax.set_ylabel('Employee')
    ax.set_title('Total Tasks Assigned to Employees')

    # Displaying the plot in the Streamlit app
    st.pyplot(fig)

# Tab 3: Task Management
with tab3:
    st.subheader("🔧 Task Management")
    selected_emp_id = st.selectbox("Manage Tasks For", options=employee_names.keys(),
                                   format_func=lambda emp_id: employee_names[emp_id])

    tasks = fetch_employee_tasks(selected_emp_id)
    if tasks:
        selected_task = st.selectbox("Select a Task", [f"{task[0]}: {task[1]}" for task in tasks])
        task_id = int(selected_task.split(":")[0])
        new_status = st.selectbox("Update Task Status", ["Pending", "In Progress", "Completed"])

        if st.button("Update Status"):
            connection = sqlite3.connect("tasks.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
            connection.commit()
            st.success("Task status updated!")
    else:
        st.write("No tasks available for management.")


