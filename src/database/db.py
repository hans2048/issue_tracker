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
        last_project_id INTEGER,
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
        resolution_text TEXT,
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
        attachment_type TEXT DEFAULT 'issue',
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

    # Activity Logs
    c.execute('''
    CREATE TABLE IF NOT EXISTS Activity_Logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action_type TEXT NOT NULL, -- e.g., 'LOGIN', 'VIEW_DASHBOARD', 'VIEW_ISSUE_LIST'
        action_detail TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (id)
    )
    ''')

    # Notices
    c.execute('''
    CREATE TABLE IF NOT EXISTS Notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_by INTEGER,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES Users (id)
    )
    ''')

    # User Notice Reads (다시 보지 않기)
    c.execute('''
    CREATE TABLE IF NOT EXISTS User_Notice_Reads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        notice_id INTEGER,
        read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (id),
        FOREIGN KEY (notice_id) REFERENCES Notices (id),
        UNIQUE(user_id, notice_id)
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

    try:
        issue_id = int(issue_id)
    except (ValueError, TypeError):
        pass

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

    # Cast issue_id to int to avoid numpy.int64 types from pandas breaking sqlite query
    try:
        issue_id = int(issue_id)
    except (ValueError, TypeError):
        pass

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
def add_revision(issue_id, modified_by, change_summary, old_content=None, new_content=None, attachment_changes=None):
    conn = get_connection()
    c = conn.cursor()

    try:
        issue_id = int(issue_id)
    except (ValueError, TypeError):
        pass

    # Check if revision_no exists, if not ignore, if yes add it
    try:
        c.execute("SELECT COUNT(*) FROM Issue_Revisions WHERE issue_id = ?", (issue_id,))
        count = c.fetchone()[0]
        revision_no = f"R{count + 1:02d}"
    except Exception:
        revision_no = None

    # If full JSON content is not explicitly provided, we will capture it ourselves.
    if old_content is None and new_content is None:
        c.execute("SELECT * FROM Issues WHERE id = ?", (issue_id,))
        current_state = c.fetchone()
        if current_state:
            import json
            state_dict = dict(current_state)
            new_content = json.dumps(state_dict, default=str)

    try:
        c.execute('''
            INSERT INTO Issue_Revisions (issue_id, modified_by, change_summary, old_content, new_content, attachment_changes, revision_no)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (issue_id, modified_by, change_summary, old_content, new_content, attachment_changes, revision_no))
    except sqlite3.OperationalError:
        # Fallback if columns don't exist yet
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

# --- Activity Logging ---
def log_activity(user_id, action_type, action_detail=None):
    if not user_id:
        return
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Activity_Logs (user_id, action_type, action_detail)
        VALUES (?, ?, ?)
    ''', (user_id, action_type, action_detail))
    conn.commit()
    conn.close()

def get_activity_stats():
    conn = get_connection()
    c = conn.cursor()
    # Get total logins and page views
    c.execute('''
        SELECT action_type, COUNT(*) as count
        FROM Activity_Logs
        GROUP BY action_type
        ORDER BY count DESC
    ''')
    stats = c.fetchall()

    # Get daily logins
    c.execute('''
        SELECT date(created_at) as log_date, COUNT(*) as count
        FROM Activity_Logs
        WHERE action_type = 'LOGIN'
        GROUP BY date(created_at)
        ORDER BY log_date ASC
    ''')
    daily_logins = c.fetchall()
    conn.close()
    return stats, daily_logins

# --- Notices ---
def create_notice(title, content, created_by):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Notices (title, content, created_by)
        VALUES (?, ?, ?)
    ''', (title, content, created_by))
    conn.commit()
    conn.close()

def update_notice_status(notice_id, is_active):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE Notices SET is_active = ? WHERE id = ?', (is_active, notice_id))
    conn.commit()
    conn.close()

def get_all_notices():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT n.*, u.username as author_name
        FROM Notices n
        LEFT JOIN Users u ON n.created_by = u.id
        ORDER BY n.created_at DESC
    ''')
    notices = c.fetchall()
    conn.close()
    return notices

def get_unread_notices_for_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT n.*
        FROM Notices n
        WHERE n.is_active = 1
        AND n.id NOT IN (
            SELECT notice_id FROM User_Notice_Reads WHERE user_id = ?
        )
        ORDER BY n.created_at DESC
    ''', (user_id,))
    notices = c.fetchall()
    conn.close()
    return notices

def mark_notice_read(user_id, notice_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO User_Notice_Reads (user_id, notice_id)
            VALUES (?, ?)
        ''', (user_id, notice_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already read
    finally:
        conn.close()


def update_project_member_role(project_id, user_id, new_role):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE Project_Members SET project_role = ? WHERE project_id = ? AND user_id = ?", (new_role, project_id, user_id))
    conn.commit()
    conn.close()

def remove_project_member(project_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM Project_Members WHERE project_id = ? AND user_id = ?", (project_id, user_id))
    conn.commit()
    conn.close()

def seed_sample_data():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Users")
    user_count = c.fetchone()[0]
    conn.close()

    if user_count > 0:
        return

    print("Seeding sample data...")
    from src.utils.auth import hash_password
    import datetime

    # 1. Create standard groups
    groups = [
        ("IT Support", "IT 인프라 및 시스템 관리"),
        ("Development", "소프트웨어 개발"),
        ("QA", "품질 보증")
    ]
    conn = get_connection()
    c = conn.cursor()
    for g, desc in groups:
        try:
            c.execute("INSERT INTO User_Groups (group_name, description) VALUES (?, ?)", (g, desc))
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()

    # 2. Create sample users
    users_data = [
        ("admin", "admin@company.com", "admin123", True, 1), # IT Support
        ("user1", "user1@company.com", "user123", False, 2), # Development
        ("user2", "user2@company.com", "user123", False, 2), # Development
        ("user3", "user3@company.com", "user123", False, 3)  # QA
    ]

    for username, email, pwd, is_sys, gid in users_data:
        create_user(username, email, hash_password(pwd), is_sys, gid)

    admin_user = get_user_by_username("admin")
    u1 = get_user_by_username("user1")
    u2 = get_user_by_username("user2")
    u3 = get_user_by_username("user3")

    # 3. Create a sample project
    create_project("신규 서비스 개발 (New Service)", "차세대 플랫폼 개발 프로젝트")
    projects = get_all_projects()
    if not projects:
        return
    pid = projects[0]['id']

    # Assign members
    add_project_member(pid, admin_user['id'], "Admin")
    add_project_member(pid, u1['id'], "Admin") # Project Admin
    add_project_member(pid, u2['id'], "Read/Write")
    add_project_member(pid, u3['id'], "Read Only")

    # Update last_project
    conn = get_connection()
    c = conn.cursor()
    for uid in [admin_user['id'], u1['id'], u2['id'], u3['id']]:
        c.execute("UPDATE Users SET last_project_id = ? WHERE id = ?", (pid, uid))
    conn.commit()
    conn.close()

    # 4. Create 3 issues per user
    users_objs = [admin_user, u1, u2, u3]
    for idx, u in enumerate(users_objs):
        for i in range(1, 4):
            due = (datetime.datetime.now() + datetime.timedelta(days=i*5)).date()
            issue_id = create_issue(
                project_id=pid,
                author_id=u['id'],
                title=f"{u['username']}님의 {i}번째 샘플 이슈",
                description=f"이것은 {u['username']}님이 작성한 {i}번째 테스트 이슈입니다.\n기능 테스트용으로 생성되었습니다.",
                priority="Medium" if i % 2 == 0 else "High",
                due_date=due,
                status="Pending"
            )
            add_revision(issue_id, u['id'], "초기 이슈 생성")

def update_user_last_project(user_id, project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE Users SET last_project_id = ? WHERE id = ?", (project_id, user_id))
    conn.commit()
    conn.close()
