import sqlite3
import datetime
import os

DB_PATH = "issue_tracker.db"

def get_connection():
    """Returns a SQLite connection object with row factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database schema and inserts default values."""
    conn = get_connection()
    c = conn.cursor()

    # User Groups
    c.execute('''
    CREATE TABLE IF NOT EXISTS User_Groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT UNIQUE NOT NULL,
        description TEXT
    )
    ''')

    # Users
    c.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        is_system_admin BOOLEAN DEFAULT 0,
        group_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES User_Groups (id)
    )
    ''')

    # Projects
    c.execute('''
    CREATE TABLE IF NOT EXISTS Projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Project Members (N:M mapping)
    c.execute('''
    CREATE TABLE IF NOT EXISTS Project_Members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        user_id INTEGER,
        project_role TEXT NOT NULL, -- Admin, Developer, User
        FOREIGN KEY (project_id) REFERENCES Projects (id),
        FOREIGN KEY (user_id) REFERENCES Users (id),
        UNIQUE(project_id, user_id)
    )
    ''')

    # Issues
    c.execute('''
    CREATE TABLE IF NOT EXISTS Issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        author_id INTEGER,
        assigned_to INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Pending', -- Pending, Open, Rejected, In Progress, Resolved, Closed
        priority TEXT DEFAULT 'Medium', -- High, Medium, Low
        due_date DATE,
        reject_reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects (id),
        FOREIGN KEY (author_id) REFERENCES Users (id),
        FOREIGN KEY (assigned_to) REFERENCES Users (id)
    )
    ''')

    # Attachments
    c.execute('''
    CREATE TABLE IF NOT EXISTS Attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        FOREIGN KEY (issue_id) REFERENCES Issues (id)
    )
    ''')

    # Issue Revisions
    c.execute('''
    CREATE TABLE IF NOT EXISTS Issue_Revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER,
        modified_by INTEGER,
        change_summary TEXT,
        modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (issue_id) REFERENCES Issues (id),
        FOREIGN KEY (modified_by) REFERENCES Users (id)
    )
    ''')

    # Insert default groups if not exist
    c.execute("SELECT COUNT(*) FROM User_Groups")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO User_Groups (group_name, description) VALUES (?, ?)", [
            ('System Admins', 'System Administrators'),
            ('Team A', 'Development Team A'),
            ('Team B', 'Development Team B'),
        ])

    conn.commit()
    conn.close()

# --- User Management ---
def get_user_by_username(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM Users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(username, email, password_hash, is_system_admin=False, group_id=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO Users (username, email, password_hash, is_system_admin, group_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, is_system_admin, group_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def get_all_groups():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM User_Groups")
    groups = c.fetchall()
    conn.close()
    return groups

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username, u.email, u.is_system_admin, g.group_name
        FROM Users u
        LEFT JOIN User_Groups g ON u.group_id = g.id
    """)
    users = c.fetchall()
    conn.close()
    return users

# --- Project Management ---
def get_all_projects():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM Projects")
    projects = c.fetchall()
    conn.close()
    return projects

def create_project(name, description):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO Projects (name, description) VALUES (?, ?)", (name, description))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_projects(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, pm.project_role
        FROM Projects p
        JOIN Project_Members pm ON p.id = pm.project_id
        WHERE pm.user_id = ?
    """, (user_id,))
    projects = c.fetchall()
    conn.close()
    return projects

def get_project_members(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT u.id, u.username, pm.project_role
        FROM Users u
        JOIN Project_Members pm ON u.id = pm.user_id
        WHERE pm.project_id = ?
    """, (project_id,))
    members = c.fetchall()
    conn.close()
    return members

def add_project_member(project_id, user_id, role):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO Project_Members (project_id, user_id, project_role) VALUES (?, ?, ?)",
                  (project_id, user_id, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- Issue Management ---
def create_issue(project_id, author_id, title, description, priority, due_date, status='Pending'):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Issues (project_id, author_id, title, description, priority, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, author_id, title, description, priority, due_date, status))
    issue_id = c.lastrowid
    conn.commit()
    conn.close()
    return issue_id

def update_issue(issue_id, **kwargs):
    conn = get_connection()
    c = conn.cursor()

    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(kwargs.values())
    values.append(issue_id)

    query = f"UPDATE Issues SET {set_clause} WHERE id = ?"
    c.execute(query, values)
    conn.commit()
    conn.close()

def get_issue(issue_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.*, p.name as project_name, u1.username as author_name, u2.username as assignee_name
        FROM Issues i
        JOIN Projects p ON i.project_id = p.id
        JOIN Users u1 ON i.author_id = u1.id
        LEFT JOIN Users u2 ON i.assigned_to = u2.id
        WHERE i.id = ?
    """, (issue_id,))
    issue = c.fetchone()
    conn.close()
    return issue

def get_issues_for_user(user_id, is_system_admin, group_id):
    """
    Returns issues based on user role and data access policy.
    - System Admin: All issues.
    - User/Team logic: Issues in projects where the user is a member,
      plus visibility into issues created by their group.
    """
    conn = get_connection()
    c = conn.cursor()

    if is_system_admin:
        c.execute("""
            SELECT i.*, p.name as project_name, u.username as author_name
            FROM Issues i
            JOIN Projects p ON i.project_id = p.id
            JOIN Users u ON i.author_id = u.id
        """)
    else:
        # Complex logic: User can see issues in their projects,
        # and issues authored by anyone in their group in those projects.
        c.execute("""
            SELECT DISTINCT i.*, p.name as project_name, u.username as author_name, pm.project_role
            FROM Issues i
            JOIN Projects p ON i.project_id = p.id
            JOIN Project_Members pm ON p.id = pm.project_id AND pm.user_id = ?
            JOIN Users u ON i.author_id = u.id
            WHERE u.group_id = ? OR pm.project_role IN ('Admin', 'Developer') OR i.author_id = ?
        """, (user_id, group_id, user_id))

    issues = c.fetchall()
    conn.close()
    return issues

def get_all_issues():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.*, p.name as project_name, u.username as author_name
        FROM Issues i
        JOIN Projects p ON i.project_id = p.id
        JOIN Users u ON i.author_id = u.id
    """)
    issues = c.fetchall()
    conn.close()
    return issues

# --- Revisions and Attachments ---
def add_revision(issue_id, modified_by, change_summary):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Issue_Revisions (issue_id, modified_by, change_summary)
        VALUES (?, ?, ?)
    ''', (issue_id, modified_by, change_summary))
    conn.commit()
    conn.close()

def get_revisions(issue_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.*, u.username as modified_by_name
        FROM Issue_Revisions r
        JOIN Users u ON r.modified_by = u.id
        WHERE r.issue_id = ?
        ORDER BY r.modified_at DESC
    """, (issue_id,))
    revisions = c.fetchall()
    conn.close()
    return revisions

def add_attachment(issue_id, filename, file_path):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Attachments (issue_id, filename, file_path)
        VALUES (?, ?, ?)
    ''', (issue_id, filename, file_path))
    conn.commit()
    conn.close()

def get_attachments(issue_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM Attachments WHERE issue_id = ?", (issue_id,))
    attachments = c.fetchall()
    conn.close()
    return attachments
