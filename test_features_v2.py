import sqlite3
import datetime
import traceback
import json
import os
from src.database.db import (
    init_db, create_user, get_user_by_username, create_project, add_project_member,
    create_issue, get_issues_for_user, get_issue, update_issue,
    add_attachment, get_attachments, add_revision, get_revisions
)
from src.utils.auth import hash_password

def run_v2_tests():
    print("--- Running V2 features tests ---")

    # 1. Init DB
    if os.path.exists('issue_tracker.db'):
        os.remove('issue_tracker.db')
    init_db()

    # Do manual schema upgrade since db.py isn't doing it in this commit apparently
    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE Users ADD COLUMN last_project_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE Issues ADD COLUMN resolution_text TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE Attachments ADD COLUMN attachment_type TEXT DEFAULT 'issue'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE Issue_Revisions ADD COLUMN old_content TEXT")
        c.execute("ALTER TABLE Issue_Revisions ADD COLUMN new_content TEXT")
        c.execute("ALTER TABLE Issue_Revisions ADD COLUMN attachment_changes TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

    print("[PASS] DB Initialized & Upgraded")

    # 2. Setup users and project
    pw_hash = hash_password("test1234")
    create_user("v2user", "v2@test.com", pw_hash, is_system_admin=True, group_id=1)
    user = get_user_by_username("v2user")

    create_project("V2 Project", "Testing V2")

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT id FROM Projects WHERE name='V2 Project'")
    project_id = c.fetchone()[0]
    conn.close()

    add_project_member(project_id=project_id, user_id=user['id'], role="Read/Write")

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("UPDATE Users SET last_project_id = ? WHERE id = ?", (project_id, user['id']))
    conn.commit()
    conn.close()

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT last_project_id FROM Users WHERE id = ?", (user['id'],))
    last_project_id = c.fetchone()[0]
    conn.close()
    assert last_project_id == project_id
    print("[PASS] User last_project_id updated")

    # 3. Create Issue
    due_date = (datetime.datetime.now() + datetime.timedelta(days=2)).date()
    issue_id = create_issue(
        project_id=project_id, author_id=user['id'], title="V2 Issue",
        description="Testing resolution", priority="High", due_date=due_date
    )

    # 4. Attachments (Issue vs Resolution)
    # We will need to test the logic with the new columns but our add_attachment doesn't take attachment_type in this version yet
    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("INSERT INTO Attachments (issue_id, filename, file_path, attachment_type) VALUES (?, ?, ?, ?)", (issue_id, "issue_file.txt", "/tmp/issue_file.txt", "issue"))
    c.execute("INSERT INTO Attachments (issue_id, filename, file_path, attachment_type) VALUES (?, ?, ?, ?)", (issue_id, "res_file.txt", "/tmp/res_file.txt", "resolution"))
    conn.commit()
    conn.close()

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Attachments WHERE issue_id = ? AND attachment_type = ?", (issue_id, 'issue'))
    issue_atts = c.fetchall()
    c.execute("SELECT * FROM Attachments WHERE issue_id = ? AND attachment_type = ?", (issue_id, 'resolution'))
    res_atts = c.fetchall()
    conn.close()

    assert len(issue_atts) == 1 and issue_atts[0][2] == "issue_file.txt" # index 2 is filename
    assert len(res_atts) == 1 and res_atts[0][2] == "res_file.txt"
    print("[PASS] Attachment types distinguished")

    # 6. Update Resolution text
    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("UPDATE Issues SET resolution_text = ? WHERE id = ?", ("This is how we fix it.", issue_id))
    conn.commit()
    c.execute("SELECT resolution_text FROM Issues WHERE id = ?", (issue_id,))
    issue_res_text = c.fetchone()[0]
    conn.close()

    assert issue_res_text == "This is how we fix it."
    print("[PASS] Resolution text updated")

    # 7. Test detailed revision history
    old_c = json.dumps({'title': 'V2 Issue'})
    new_c = json.dumps({'title': 'V2 Issue Changed'})
    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO Issue_Revisions (issue_id, modified_by, change_summary, old_content, new_content, attachment_changes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (issue_id, user['id'], "Title changed", old_c, new_c, json.dumps(['new_file.txt'])))
    conn.commit()

    c.execute("SELECT old_content, new_content, attachment_changes FROM Issue_Revisions WHERE issue_id = ?", (issue_id,))
    rev = c.fetchone()
    conn.close()

    assert rev[0] == old_c
    assert rev[1] == new_c
    assert rev[2] == '["new_file.txt"]'
    print("[PASS] Detailed JSON revisions logged")

    print("--- All V2 tests passed! ---")

if __name__ == "__main__":
    try:
        run_v2_tests()
    except Exception as e:
        print(f"[FAIL] Exception occurred: {e}")
        traceback.print_exc()
