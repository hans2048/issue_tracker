import sqlite3
import datetime
import traceback
from src.database.db import (
    init_db, create_user, get_user_by_username,
    log_activity, get_activity_stats,
    create_notice, get_all_notices, get_unread_notices_for_user, mark_notice_read, update_notice_status
)
from src.utils.auth import hash_password

def run_notices_tests():
    print("--- Running notices & tracking tests ---")

    # 1. Init DB
    init_db()
    print("[PASS] DB Initialized")

    # 2. Setup user
    pw_hash = hash_password("admin123")
    create_user("admin2", "admin2@test.com", pw_hash, is_system_admin=True, group_id=1)
    admin_user = get_user_by_username("admin2")
    assert admin_user is not None
    user_id = admin_user['id']

    # 3. Test Activity Tracking
    log_activity(user_id, 'LOGIN')
    log_activity(user_id, 'VIEW_DASHBOARD')
    log_activity(user_id, 'VIEW_NOTICES')
    stats, daily_logins = get_activity_stats()
    assert len(stats) >= 3 # We expect LOGIN, VIEW_DASHBOARD, VIEW_NOTICES
    assert len(daily_logins) >= 1
    print("[PASS] Activity tracking tested")

    # 4. Test Notices Creation
    create_notice("System Maintenance", "Downtime expected at midnight.", user_id)
    notices = get_all_notices()
    assert len(notices) >= 1
    notice_id = notices[0]['id']
    print("[PASS] Notice created")

    # 5. Test Unread Notices functionality
    unread = get_unread_notices_for_user(user_id)
    assert len(unread) >= 1
    assert unread[0]['title'] == "System Maintenance"

    mark_notice_read(user_id, notice_id)
    unread_after = get_unread_notices_for_user(user_id)
    assert len(unread_after) == len(unread) - 1
    print("[PASS] Notice read functionality tested")

    # 6. Test Notice Deactivation
    update_notice_status(notice_id, 0) # Deactivate
    notices_after = get_all_notices()
    assert notices_after[0]['is_active'] == 0
    print("[PASS] Notice status update tested")

    print("--- All notices & tracking tests passed! ---")

if __name__ == "__main__":
    try:
        run_notices_tests()
    except Exception as e:
        print(f"[FAIL] Exception occurred: {e}")
        traceback.print_exc()
