import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

# Paths
CHECKLIST_PATH = "data/master_checklist.json"
AUDIT_LOG_PATH = "data/audit_logs/"
ASSIGNMENTS_PATH = "data/assignments.json"
USERS_PATH = "data/users.json"

# Default users
DEFAULT_USERS = {
    "manager": {"password": "admin123", "role": "manager"},
    "employee1": {"password": "emp123", "role": "employee"},
    "employee2": {"password": "emp456", "role": "employee"},
}

# Ensure directories and files exist
os.makedirs("data", exist_ok=True)
os.makedirs(AUDIT_LOG_PATH, exist_ok=True)
if not os.path.exists(CHECKLIST_PATH):
    with open(CHECKLIST_PATH, "w") as f:
        json.dump([], f)
if not os.path.exists(ASSIGNMENTS_PATH):
    with open(ASSIGNMENTS_PATH, "w") as f:
        json.dump({}, f)
if not os.path.exists(USERS_PATH):
    with open(USERS_PATH, "w") as f:
        json.dump(DEFAULT_USERS, f, indent=4)

# Load/save functions
def load_master_checklist():
    with open(CHECKLIST_PATH, "r") as f:
        return json.load(f)

def save_master_checklist(data):
    with open(CHECKLIST_PATH, "w") as f:
        json.dump(data, f, indent=4)

def load_users():
    with open(USERS_PATH, "r") as f:
        return json.load(f)

def load_assignments():
    with open(ASSIGNMENTS_PATH, "r") as f:
        return json.load(f)

def save_assignments(data):
    with open(ASSIGNMENTS_PATH, "w") as f:
        json.dump(data, f, indent=4)

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

def login():
    st.title("🔐 IFC Tool Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    users = load_users()
    if st.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = users[username]["role"]
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username or password")

def master_checklist_page():
    st.title("📝 Master Checklist Manager")
    checklist = load_master_checklist()
    users = load_users()
    assignments = load_assignments()

    with st.form("Add Checklist Item"):
        question = st.text_input("Checklist Question")
        input_type = st.selectbox("Input Type", ["Yes/No", "Dropdown", "Text"])
        options = ""
        if input_type == "Dropdown":
            options = st.text_input("Dropdown Options (comma-separated)")
        submitted = st.form_submit_button("Add")
        if submitted and question:
            checklist.append({
                "id": len(checklist),
                "question": question,
                "input_type": input_type,
                "options": [opt.strip() for opt in options.split(",")] if options else []
            })
            save_master_checklist(checklist)
            st.success("Checklist item added!")

    st.subheader("Assign Checklist to Employees")
    new_assignments = {}
    for user in users:
        if users[user]["role"] == "employee":
            options = [f"{c['id']}: {c['question']}" for c in checklist]
            existing_assignment_ids = assignments.get(user, [])
            pre_selected = [f"{c['id']}: {c['question']}" for c in checklist if c['id'] in existing_assignment_ids]
            selected = st.multiselect(f"Assign to {user}", options, default=pre_selected, key=user)
            new_assignments[user] = [int(item.split(":")[0]) for item in selected]

    if st.button("💾 Save Changes"):
        save_assignments(new_assignments)
        st.success("Assignments saved successfully!")

    st.subheader("Existing Checklist Items")
    for idx, item in enumerate(checklist):
        st.markdown(f"**{idx+1}. {item['question']}** ({item['input_type']})")
        if item['input_type'] == 'Dropdown':
            st.markdown(f"Options: {', '.join(item['options'])}")
        if st.button(f"❌ Delete {idx+1}"):
            checklist.pop(idx)
            for i, itm in enumerate(checklist):
                itm['id'] = i
            save_master_checklist(checklist)
            st.rerun()

def employee_checklist_page():
    st.title("✅ Fill Assigned Checklist")
    checklist = load_master_checklist()
    assignments = load_assignments()
    username = st.session_state.username
    assigned_ids = assignments.get(username, [])
    assigned_items = [item for item in checklist if item["id"] in assigned_ids]

    client_name = st.text_input("Client Name")
    audit_period = st.text_input("Audit Period")
    responses = []

    st.subheader("Answer the following:")
    for item in assigned_items:
        st.markdown(f"**{item['question']}**")
        answer = ""
        if item['input_type'] == "Yes/No":
            answer = st.radio(item['question'], ["Yes", "No"], key=item['question'] + username, index=None)
        elif item['input_type'] == "Dropdown":
            answer = st.selectbox(item['question'], ["Select"] + item['options'], key=item['question'] + username)
            answer = "" if answer == "Select" else answer
        else:
            answer = st.text_input(item['question'], key=item['question'] + username)
        responses.append({"question": item['question'], "answer": answer})

    if st.button("Submit Audit"):
        df = pd.DataFrame(responses)
        df.insert(0, "Client", client_name)
        df.insert(1, "Audit Period", audit_period)
        filename = f"{AUDIT_LOG_PATH}{client_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False)
        st.success(f"Audit saved to {filename}")

    if os.listdir(AUDIT_LOG_PATH):
        st.subheader("📥 Download Previous Audits")
        files = sorted(os.listdir(AUDIT_LOG_PATH), reverse=True)
        selected_file = st.selectbox("Select a file to download", files)
        if selected_file:
            file_path = os.path.join(AUDIT_LOG_PATH, selected_file)
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            st.download_button(
                label="Download Selected Audit",
                data=file_bytes,
                file_name=selected_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# MAIN APP
if not st.session_state.logged_in:
    login()
else:
    st.sidebar.write(f"👤 Logged in as: {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.role == "manager":
        master_checklist_page()
    elif st.session_state.role == "employee":
        employee_checklist_page()
