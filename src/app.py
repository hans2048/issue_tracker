import streamlit as st
import os
import sys

# Ensure the parent directory is in sys.path so 'src' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db import init_db, get_all_groups
from src.utils.auth import login, signup, logout
from src.ui.dashboard import render_dashboard
from src.ui.issue_list import render_issue_list
from src.ui.issue_detail import render_issue_create, render_issue_detail
from src.ui.admin import render_admin_dashboard
from src.ui.notices import check_and_show_notices, render_notice_history
from src.database.db import log_activity

from src.database.db import seed_sample_data

# Ensure database is initialized
if not os.path.exists('issue_tracker.db'):
    init_db()
    seed_sample_data()
else:
    # Just in case we need to make sure default data is in place
    init_db()


st.set_page_config(page_title="Issue Tracker", layout="wide")

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['current_view'] = 'Dashboard'

    if not st.session_state['logged_in']:
        render_auth_page()
    else:
        render_main_app()

def render_auth_page():
    st.title("사내 이슈 트래커 (Issue Tracker)")

    tab1, tab2 = st.tabs(["로그인 (Login)", "회원가입 (Sign Up)"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("로그인")

            if submit:
                if login(username, password):
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 잘못되었습니다.")

    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")

            groups = get_all_groups()
            group_options = {g['group_name']: g['id'] for g in groups}
            selected_group = st.selectbox("소속 그룹 (Team/Department)", list(group_options.keys()))

            signup_submit = st.form_submit_button("회원가입")

            if signup_submit:
                if not new_username or not new_email or not new_password:
                    st.error("모든 필드를 입력해주세요.")
                else:
                    group_id = group_options[selected_group]
                    if signup(new_username, new_email, new_password, group_id):
                        st.success("회원가입 완료! 로그인 탭에서 로그인해주세요.")
                    else:
                        st.error("이미 존재하는 Username 입니다.")

def render_main_app():
    # Check for notices on load
    check_and_show_notices()

    # Sidebar navigation
    with st.sidebar:
        st.write(f"환영합니다, **{st.session_state['username']}**님!")
        if st.session_state.get('is_system_admin'):
            st.markdown("*(System Admin)*")

        st.divider()

        # Navigation logic
        if st.button("대시보드 (Dashboard)", use_container_width=True):
            st.session_state['current_view'] = 'Dashboard'
            st.rerun()

        if st.button("이슈 목록 (Issue List)", use_container_width=True):
            st.session_state['current_view'] = 'Issue List'
            st.rerun()

        if st.button("새 이슈 등록 (New Issue)", use_container_width=True):
            st.session_state['current_view'] = 'New Issue'
            st.rerun()

        if st.button("공지사항 (Notices)", use_container_width=True):
            st.session_state['current_view'] = 'Notices'
            st.rerun()

        if st.session_state.get('is_system_admin') or has_admin_projects():
            if st.button("관리자 메뉴 (Admin)", use_container_width=True):
                st.session_state['current_view'] = 'Admin'
                st.rerun()

        st.divider()
        if st.button("로그아웃 (Logout)", use_container_width=True):
            logout()
            st.rerun()

    # Route to the selected view
    view = st.session_state.get('current_view', 'Dashboard')

    # Log page view if changed (basic analytics)
    if 'last_view' not in st.session_state or st.session_state['last_view'] != view:
        log_activity(st.session_state.get('user_id'), f'VIEW_{view.upper().replace(" ", "_")}')
        st.session_state['last_view'] = view

    if view == 'Dashboard':
        render_dashboard()
    elif view == 'Issue List':
        render_issue_list()
    elif view == 'New Issue':
        render_issue_create()
    elif view == 'Issue Detail':
        render_issue_detail()
    elif view == 'Notices':
        render_notice_history()
    elif view == 'Admin':
        render_admin_dashboard()

def has_admin_projects():
    """Helper to check if current user is admin of any project."""
    from src.database.db import get_user_projects
    user_id = st.session_state.get('user_id')
    if not user_id: return False
    projects = get_user_projects(user_id)
    return any(p['project_role'] == 'Admin' for p in projects)

if __name__ == "__main__":
    main()
