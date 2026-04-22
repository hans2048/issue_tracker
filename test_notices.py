import sqlite3
import datetime
import traceback
import os
from src.database.db import init_db, create_user, get_user_by_username, log_activity, create_notice, get_unread_notices_for_user, mark_notice_read
from src.utils.auth import hash_password

def run_notices_tests():
    print("--- Running notices & tracking tests ---")

    # 1. Init DB
    if os.path.exists('issue_tracker.db'):
        os.remove('issue_tracker.db')
    init_db()
    print("[PASS] DB Initialized")

    # Setup user
    pw_hash = hash_password("test1234")
    create_user("noticeuser", "nu@test.com", pw_hash, is_system_admin=False, group_id=1)
    user = get_user_by_username("noticeuser")

    # 2. Test activity tracking
    log_activity(user['id'], "LOGIN_SUCCESS")

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Activity_Logs WHERE user_id = ?", (user['id'],))
    logs = c.fetchall()
    conn.close()

    assert len(logs) == 1
    assert logs[0][2] == "LOGIN_SUCCESS"
    print("[PASS] Activity tracking tested")

    # 3. Test notice creation
    create_notice("Test Notice", "This is a test notice.", user['id'])

    conn = sqlite3.connect('issue_tracker.db')
    c = conn.cursor()
    c.execute("SELECT id FROM Notices WHERE title = 'Test Notice'")
    notice_id = c.fetchone()[0]
    conn.close()

    assert notice_id > 0
    print("[PASS] Notice created")

    # 4. Test reading notice (should be active since we haven't marked it read)
    active = get_unread_notices_for_user(user['id'])
    assert len(active) == 1
    assert active[0]['title'] == "Test Notice"
    print("[PASS] Notice read functionality tested")

    # 5. Mark as read and check again
    mark_notice_read(user['id'], notice_id)
    active_after = get_unread_notices_for_user(user['id'])
    assert len(active_after) == 0
    print("[PASS] Notice status update tested")

    print("--- All notices & tracking tests passed! ---")

if __name__ == "__main__":
    try:
        run_notices_tests()
    except Exception as e:
        print(f"[FAIL] Exception occurred: {e}")
        traceback.print_exc()
