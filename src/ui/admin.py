import streamlit as st
import pandas as pd
from src.database.db import (
    get_all_users, get_all_groups, get_all_projects, create_project,
    get_project_members, add_project_member, get_user_projects
)

def render_admin_dashboard():
    st.header("관리자 메뉴 (Admin Menu)")

    is_system_admin = st.session_state.get('is_system_admin')
    user_id = st.session_state.get('user_id')

    tabs = []
    if is_system_admin:
        tabs = st.tabs(["사용자 관리", "프로젝트 관리", "시스템 설정"])

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
