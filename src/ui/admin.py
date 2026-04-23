import streamlit as st
import pandas as pd
import plotly.express as px
from src.database.db import (
    get_all_users, get_all_groups, get_all_projects, create_project,
    get_project_members, add_project_member, get_user_projects,
    get_activity_stats, create_notice, get_all_notices, update_notice_status,
    update_project_member_role, remove_project_member
)

def render_admin_dashboard():
    st.header("관리자 메뉴 (Admin Menu)")

    is_system_admin = st.session_state.get('is_system_admin')
    user_id = st.session_state.get('user_id')
    username = st.session_state.get('username')

    if username != 'admin':
        st.error("접근 권한이 없습니다. (Access Denied)")
        return

    tabs = []
    if True: # Admin user is always sysadmin effectively for this view based on new logic
        tabs = st.tabs(["사용자 관리", "프로젝트 관리", "공지사항 관리", "접속현황 모니터링", "시스템 설정"])

        with tabs[0]:
            st.subheader("사용자 목록 (Users)")
            users = get_all_users()
            if users:
                df_users = pd.DataFrame([dict(u) for u in users])
                st.dataframe(df_users, hide_index=True)
