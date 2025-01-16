import streamlit as st
import sqlite3
from datetime import date, timedelta
import pandas as pd
from docx import Document
import matplotlib.pyplot as plt


# Initialize SQLite database
def init_db():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    # Create tasks table if it doesn't exist
    cursor.execute(""" CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            status TEXT DEFAULT 'Pending',
            assigned_to TEXT,
            deadline DATE,
            file_path TEXT
        )
    """)

    # Create employees table with their departments
    cursor.execute(""" CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT
        )
    """)
    connection.commit()

    return connection



# Add a task to the database
def add_task(title, description, category, assigned_to, deadline, file_path=None):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute(""" INSERT INTO tasks (title, description, category, assigned_to, deadline, file_path)
                      VALUES (?, ?, ?, ?, ?, ?) """, (title, description, category, assigned_to, deadline, file_path))
    connection.commit()

    # Success notification after task addition
    st.success(f"New Task Assigned: {title} - Deadline: {deadline}")


# Add an employee to the database
def add_employee(name, department):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("""INSERT INTO employees (name, department) VALUES (?, ?)""", (name, department))
    connection.commit()


# Fetch tasks for a specific employee
def fetch_employee_tasks(employee_name):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM tasks WHERE assigned_to = ?", (employee_name,))
    return cursor.fetchall()


# Function to calculate remaining time
def get_remaining_time(deadline):
    now = date.today()
    deadline_date = pd.to_datetime(deadline).date()
    remaining_time = deadline_date - now
    return remaining_time.days


# Function to update task status
def update_task_status(task_id, status):
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    connection.commit()


# Function to parse uploaded file (CSV or DOCX)
def parse_file(uploaded_file):
    if uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        return df.head().to_string()
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])


# Function to display status bulb (red, yellow, green)
def status_bulb(status, remaining_time):
    if status == "Completed":
        return "🟢", "green"
    elif remaining_time <= 0:
        return "🔴", "red"
    elif remaining_time <= 2:
        return "🟡", "yellow"
    else:
        return "🟢", "green"


# Function to visualize task status distribution
def plot_task_status_distribution():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    status_counts = cursor.fetchall()
    connection.close()

    labels = [status[0] for status in status_counts]
    sizes = [status[1] for status in status_counts]

    # Plotting the pie chart
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=["#ff9999", "#66b3ff", "#99ff99"])
    ax.axis('equal')  # Equal aspect ratio ensures that pie chart is drawn as a circle.
    st.pyplot(fig)


# Function to visualize remaining time for tasks
def plot_remaining_time():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT title, deadline FROM tasks")
    tasks = cursor.fetchall()
    connection.close()

    titles = []
    remaining_days = []

    for task in tasks:
        titles.append(task[0])
        remaining_days.append(get_remaining_time(task[1]))

    # Bar Chart
    fig, ax = plt.subplots()
    ax.barh(titles, remaining_days, color=["red" if x <= 0 else "green" for x in remaining_days])
    ax.set_xlabel('Remaining Days')
    ax.set_ylabel('Task Titles')
    ax.set_title('Remaining Time for Tasks')
    st.pyplot(fig)


# Function to visualize employee task assignments
def plot_employee_task_assignments():
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT assigned_to, COUNT(*) FROM tasks GROUP BY assigned_to")
    task_assignments = cursor.fetchall()
    connection.close()

    employees = [task[0] for task in task_assignments]
    num_tasks = [task[1] for task in task_assignments]

    # Bar Chart
    fig, ax = plt.subplots()
    ax.barh(employees, num_tasks, color='skyblue')
    ax.set_xlabel('Number of Tasks')
    ax.set_ylabel('Employee')
    ax.set_title('Tasks Assigned to Each Employee')
    st.pyplot(fig)

# Initialize Streamlit app
# Initialize Streamlit app
st.image("IOJH-logo.jpeg", width=100)  # Display logo at the top of the app
st.title("Task Management App")  # Title text for the app

  # Replace with your logo file path and set the desired width


# Initialize the database
connection = init_db()

# Sidebar for employee list and actions
with st.sidebar:
    st.header("Employee Dashboard")

    # Fetch list of employees and departments
    connection = sqlite3.connect("tasks.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    # Display employees and departments in the sidebar
    employee_dict = {emp[0]: f"{emp[1]} - {emp[2]}" for emp in employees}  # {ID: 'Name - Department'}
    selected_employee = st.selectbox("Select Employee", options=employee_dict.keys())

    # Display selected employee's department
    if selected_employee:
        st.write(f"**Department**: {employee_dict[selected_employee]}")

    uploaded_file = st.file_uploader("Upload a DOCX or CSV file", type=["csv", "docx"])
    assigned_to = st.text_input("Assign to Employee", value=employee_dict.get(selected_employee, ""))
    deadline = st.date_input("Set Project Deadline", min_value=date.today())

    # New Employee login field
    employee_name = st.text_input("Enter Employee Name to Access Dashboard")

    if uploaded_file and assigned_to:
        file_content = parse_file(uploaded_file)
        st.write(f"File preview: \n{file_content}")

        # Add task with file and deadline info
        if st.button("Assign Task"):
            add_task(
                title=f"Task for {assigned_to}",
                description=file_content,
                category="Project",
                assigned_to=assigned_to,
                deadline=deadline,
                file_path=uploaded_file.name
            )
            st.success("Project assigned successfully!")

# Tabs for better organization
# Visualizations Tab
tab1, tab2, tab3, tab4 = st.tabs(["📋 View Tasks", "➕ Add Task", "🛠 Manage Tasks", "📊 Task Visualizations"])

# Tab 1: View Tasks
with tab1:
    st.subheader("📋 All Tasks")
    tasks = fetch_employee_tasks(employee_name)

    if tasks:
        for task in tasks:
            # Display task info
            st.markdown(f"### Task: {task[1]}")
            st.markdown(f"**Category:** {task[3]}")
            st.markdown(f"**Assigned To:** {task[5]}")
            st.markdown(f"**Deadline:** {task[6]}")
            st.markdown(f"**Status:** {task[4]}")

            # Calculate remaining time
            remaining_days = get_remaining_time(task[6])

            # Display status bulb and remaining time
            bulb, color = status_bulb(task[4], remaining_days)
            status_display = f"{bulb} Status: {task[4]} | Remaining Time: {remaining_days} days"
            st.markdown(f"<div style='text-align:right;color:{color};'>{status_display}</div>", unsafe_allow_html=True)

            if len(task) > 7 and task[7]:
                st.markdown(f"**File Uploaded:** {task[7]}")

            st.divider()
    else:
        st.write("No tasks found. Please enter a valid employee name to view tasks.")

# Tab 2: Add Task (with hidden description)
with tab2:
    st.subheader("➕ Add a New Task")

    with st.form("Add Task Form"):
        title = st.text_input("Title")
        category = st.text_input("Category")
        assigned_to = st.text_input("Assigned To")
        deadline = st.date_input("Deadline", min_value=date.today())

        submit_button = st.form_submit_button("Add Task")

        # After the task is submitted, it should re-fetch tasks to reflect updates.
        if submit_button:
            if title and assigned_to:
                # Add the task
                add_task(title, "", category, assigned_to, deadline)  # Empty description field

                # Refresh and show success notification
                st.success("Task added successfully!")

                # Fetch tasks again after adding one
                tasks = fetch_employee_tasks(employee_name)

                if tasks:
                    for task in tasks:
                        # Display task info
                        st.markdown(f"### Task: {task[1]}")
                        st.markdown(f"**Category:** {task[3]}")
                        st.markdown(f"**Assigned To:** {task[5]}")
                        st.markdown(f"**Deadline:** {task[6]}")
                        st.markdown(f"**Status:** {task[4]}")

                        # Calculate remaining time
                        remaining_days = get_remaining_time(task[6])

                        # Display status bulb and remaining time
                        bulb, color = status_bulb(task[4], remaining_days)
                        status_display = f"{bulb} Status: {task[4]} | Remaining Time: {remaining_days} days"
                        st.markdown(f"<div style='text-align:right;color:{color};'>{status_display}</div>", unsafe_allow_html=True)

                        if len(task) > 7 and task[7]:
                            st.markdown(f"**File Uploaded:** {task[7]}")

                        st.divider()
                else:
                    st.write("No tasks found. Please try again.")
            else:
                st.error("Title and Assigned To are required fields!")

# Tab 3: Manage Tasks
with tab3:
    st.subheader("🛠 Manage Tasks")
    tasks = fetch_employee_tasks(employee_name)

    if tasks:
        task_id = st.selectbox("Select Task to Update or Delete", [f"{task[0]}: {task[1]}" for task in tasks])
        selected_task_id = int(task_id.split(":")[0])

        # Update Status
        new_status = st.selectbox("Update Status", ["Pending", "In Progress", "Completed"])
        if st.button("Update Status"):
            update_task_status(selected_task_id, new_status)
            st.success("Task status updated!")

        # Delete Task
        if st.button("Delete Task"):
            delete_task(selected_task_id)
            st.warning("Task deleted successfully!")
    else:
        st.write("No tasks available for management.")


# Tab 4: Task Visualizations
with tab4:
    st.subheader("📊 Task Status Distribution")
    plot_task_status_distribution()

    st.subheader("🕒 Remaining Time for Tasks")
    plot_remaining_time()

    st.subheader("👨‍💼 Tasks Assigned to Employees")
    plot_employee_task_assignments()

# Clean up database connection
connection.close()
