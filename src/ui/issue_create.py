import streamlit as st
import os
from src.database.db import create_issue, add_revision, add_attachment, get_user_projects

UPLOAD_DIR = "uploads"

def render_issue_create():
    st.header("새 이슈 등록 (Create New Issue)")

    user_id = st.session_state.get('user_id')
    projects = get_user_projects(user_id)

    if not projects:
        st.warning("소속된 프로젝트가 없습니다. 시스템 관리자나 프로젝트 관리자에게 권한을 요청하세요.")
        return

    project_options = {p['name']: p['id'] for p in projects}
    selected_project_name = st.selectbox("프로젝트 선택 (Select Project)", list(project_options.keys()))

    title = st.text_input("제목 (Title)")
    description = st.text_area("내용 (Description)")
    priority = st.selectbox("중요도 (Priority)", ["Low", "Medium", "High"], index=1)
    due_date = st.date_input("완료 목표일 (Due Date)")

    uploaded_files = st.file_uploader("첨부파일 (Attachments)", accept_multiple_files=True)

    if st.button("등록 (Submit)"):
        if not title:
            st.error("제목을 입력하세요.")
            return

        project_id = project_options[selected_project_name]

        # New issues default to Pending
        issue_id = create_issue(
            project_id=project_id,
            author_id=user_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            status='Pending'
        )

        add_revision(issue_id, user_id, "이슈 생성 (Issue Created)")

        # Handle file uploads
        if uploaded_files:
            if not os.path.exists(UPLOAD_DIR):
                os.makedirs(UPLOAD_DIR)
            for file in uploaded_files:
                file_path = os.path.join(UPLOAD_DIR, f"{issue_id}_{file.name}")
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                add_attachment(issue_id, file.name, file_path)

        st.success(f"이슈 #{issue_id} 등록이 완료되었습니다. (승인 대기 중)")
        st.session_state['current_view'] = 'Issue List'
        st.rerun()
