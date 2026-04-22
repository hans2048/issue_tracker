import streamlit as st
import pandas as pd
import plotly.express as px
from src.database.db import (
    get_all_users, get_all_groups, get_all_projects, create_project,
    get_project_members, add_project_member, get_user_projects,
    get_activity_stats, create_notice, get_all_notices, update_notice_status
)

def render_admin_dashboard():
    st.header("관리자 메뉴 (Admin Menu)")

    is_system_admin = st.session_state.get('is_system_admin')
    user_id = st.session_state.get('user_id')

    tabs = []
    if is_system_admin:
        tabs = st.tabs(["사용자 관리", "프로젝트 관리", "공지사항 관리", "접속현황 모니터링", "시스템 설정"])

        with tabs[0]:
            st.subheader("사용자 목록 (Users)")
            users = get_all_users()
            if users:
                df_users = pd.DataFrame([dict(u) for u in users])
                st.dataframe(df_users, hide_index=True)
            else:
                st.write("등록된 사용자가 없습니다.")

        with tabs[1]:
            st.subheader("프로젝트 목록 (Projects)")
            projects = get_all_projects()
            if projects:
                df_projects = pd.DataFrame([dict(p) for p in projects])
                st.dataframe(df_projects, hide_index=True)

            st.subheader("새 프로젝트 생성 (Create Project)")
            new_proj_name = st.text_input("프로젝트 명 (Project Name)")
            new_proj_desc = st.text_area("프로젝트 설명 (Description)")
            if st.button("프로젝트 생성"):
                if new_proj_name:
                    if create_project(new_proj_name, new_proj_desc):
                        st.success(f"'{new_proj_name}' 생성 완료")
                        st.rerun()
                    else:
                        st.error("이미 존재하는 프로젝트 명입니다.")
                else:
                    st.error("프로젝트 명을 입력하세요.")

            st.divider()

            # System Admin can assign members to any project
            st.subheader("프로젝트 멤버 할당 (Assign Members)")
            if projects and users:
                proj_options = {p['name']: p['id'] for p in projects}
                sel_proj = st.selectbox("프로젝트 선택", list(proj_options.keys()), key="sys_proj_sel")

                user_options = {f"{u['username']} ({u['email']})": u['id'] for u in users}
                sel_user = st.selectbox("사용자 선택", list(user_options.keys()), key="sys_user_sel")

                role = st.selectbox("권한", ["Admin", "Developer", "User"], key="sys_role_sel")

                if st.button("멤버 추가", key="sys_add_member"):
                    if add_project_member(proj_options[sel_proj], user_options[sel_user], role):
                        st.success("멤버 추가 성공")
                    else:
                        st.error("이미 할당된 사용자이거나 오류가 발생했습니다.")

        with tabs[2]:
            st.subheader("새 공지사항 등록 (Create Notice)")
            with st.form("create_notice_form"):
                notice_title = st.text_input("제목 (Title)")
                notice_content = st.text_area("내용 (Content)")
                submit_notice = st.form_submit_button("등록")
                if submit_notice:
                    if notice_title and notice_content:
                        create_notice(notice_title, notice_content, user_id)
                        st.success("공지사항이 등록되었습니다.")
                        st.rerun()
                    else:
                        st.error("제목과 내용을 입력하세요.")

            st.divider()
            st.subheader("공지사항 관리 (Manage Notices)")
            notices = get_all_notices()
            if notices:
                for notice in notices:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{notice['title']}** (작성일: {notice['created_at']})")
                        st.write(f"상태: {'활성' if notice['is_active'] else '비활성'}")
                    with col2:
                        action_label = "비활성화" if notice['is_active'] else "활성화"
                        if st.button(action_label, key=f"toggle_notice_{notice['id']}"):
                            update_notice_status(notice['id'], not notice['is_active'])
                            st.rerun()
                    st.write("---")
            else:
                st.write("등록된 공지사항이 없습니다.")

        with tabs[3]:
            st.subheader("접속현황 모니터링 (Activity Monitoring)")

            stats, daily_logins = get_activity_stats()

            if not stats and not daily_logins:
                st.info("기록된 활동 내역이 없습니다.")
            else:
                # 1. Action frequencies
                if stats:
                    df_stats = pd.DataFrame(stats, columns=['action_type', 'count'])
                    fig_stats = px.bar(df_stats, x='action_type', y='count', title='기능 사용 빈도 (Feature Usage Frequency)')
                    st.plotly_chart(fig_stats, use_container_width=True)

                # 2. Daily Logins
                if daily_logins:
                    df_logins = pd.DataFrame(daily_logins, columns=['log_date', 'count'])
                    fig_logins = px.line(df_logins, x='log_date', y='count', title='일별 로그인 현황 (Daily Logins)', markers=True)
                    st.plotly_chart(fig_logins, use_container_width=True)

        with tabs[4]:
            st.subheader("시스템 그룹 (User Groups)")
            groups = get_all_groups()
            if groups:
                df_groups = pd.DataFrame([dict(g) for g in groups])
                st.dataframe(df_groups, hide_index=True)

    else:
        # Project Admin view
        projects = get_user_projects(user_id)
        admin_projects = [p for p in projects if p['project_role'] == 'Admin']

        if not admin_projects:
            st.warning("프로젝트 관리자 권한이 없습니다.")
            return

        st.subheader("내 프로젝트 관리 (Manage My Projects)")
        proj_options = {p['name']: p['id'] for p in admin_projects}
        sel_proj = st.selectbox("프로젝트 선택", list(proj_options.keys()))

        proj_id = proj_options[sel_proj]
        members = get_project_members(proj_id)

        st.write("현재 멤버 목록:")
        if members:
            df_members = pd.DataFrame([dict(m) for m in members])
            st.dataframe(df_members, hide_index=True)

        st.divider()
        st.write("새 멤버 추가")
        all_users = get_all_users()
        if all_users:
            user_options = {f"{u['username']}": u['id'] for u in all_users}
            sel_user = st.selectbox("사용자 선택", list(user_options.keys()))
            role = st.selectbox("권한", ["Developer", "User"]) # Usually Project Admins don't assign other Admins easily, but we'll allow Dev/User

            if st.button("멤버 추가"):
                if add_project_member(proj_id, user_options[sel_user], role):
                    st.success("멤버 추가 성공")
                    st.rerun()
                else:
                    st.error("이미 할당된 사용자이거나 오류가 발생했습니다.")
