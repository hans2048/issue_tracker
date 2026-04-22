import sqlite3
import datetime
import traceback
from src.database.db import init_db, create_user, get_user_by_username, create_project, add_project_member, create_issue, get_issues_for_user
from src.utils.auth import hash_password

def run_tests():
    print("--- Running tests ---")

    # 1. Init DB
    init_db()
    print("[PASS] DB Initialized")

    # 2. Create System Admin
    pw_hash = hash_password("admin123")
    create_user("admin", "admin@test.com", pw_hash, is_system_admin=True, group_id=1)
    admin_user = get_user_by_username("admin")
    assert admin_user is not None
    print("[PASS] System Admin created")

    # 3. Create Regular User
    pw_hash = hash_password("user123")
    create_user("testuser", "user@test.com", pw_hash, is_system_admin=False, group_id=2) # Group 2 is Team A
    regular_user = get_user_by_username("testuser")
    assert regular_user is not None
    print("[PASS] Regular user created")

    # 4. Create Project
    create_project("Project Alpha", "First test project")
    print("[PASS] Project created")

    # 5. Add user to project as User
    add_project_member(project_id=1, user_id=regular_user['id'], role="User")
    print("[PASS] Added user to project")

    # 6. Create Issue
    due_date = (datetime.datetime.now() + datetime.timedelta(days=2)).date()
    issue_id = create_issue(
        project_id=1,
        author_id=regular_user['id'],
        title="Test Issue 1",
        description="This is a test issue",
        priority="High",
        due_date=due_date,
        status="Pending"
    )
    assert issue_id > 0
    print("[PASS] Created issue")

    # 7. Test get_issues_for_user visibility
    issues = get_issues_for_user(regular_user['id'], False, regular_user['group_id'])
    assert len(issues) == 1
    assert issues[0]['title'] == "Test Issue 1"
    print("[PASS] Issue visibility tested")

    print("--- All tests passed! ---")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"[FAIL] Exception occurred: {e}")
        traceback.print_exc()
