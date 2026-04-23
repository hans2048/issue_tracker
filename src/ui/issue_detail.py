import streamlit as st
import os
from datetime import datetime
from src.database.db import (
    get_issue, update_issue, add_revision, get_revisions,
    add_attachment, get_attachments, create_issue, get_user_projects, get_project_members
)

UPLOAD_DIR = "uploads"

def render_issue_detail():
    issue_id = st.session_state.get('selected_issue_id')
    if not issue_id:
        st.warning("선택된 이슈가 없습니다.")
        if st.button("목록으로 돌아가기"):
            st.session_state['current_view'] = 'Issue List'
            st.rerun()
        return

    issue = get_issue(issue_id)
    if not issue:
        st.error("이슈를 찾을 수 없습니다.")
        return

    # 사용자 권한 확인 로직 (본인 그룹 작성글은 수정 가능)
    # Get user role in this project
    user_id = st.session_state.get('user_id')
    is_system_admin = st.session_state.get('is_system_admin')
    user_group_id = st.session_state.get('group_id')

    projects = get_user_projects(user_id)
    user_role = next((p['project_role'] for p in projects if p['id'] == issue['project_id']), None)
    if is_system_admin:
        user_role = 'Admin'

    # 같은 그룹인지 확인하기 위해 DB에서 작성자 정보를 조회하여 group_id 비교
    # (간단하게는 DB에서 join해서 가져왔어야 하지만, 여기서는 직접 체크하거나 issue author를 가져옴)
    # We'll use a separate query just to be safe if group_id is not in issue dict.
    from src.database.db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT group_id FROM Users WHERE id = ?", (issue['author_id'],))
    author_group = c.fetchone()[0]
    conn.close()

    # 수정 가능 권한: 시스템 관리자, 프로젝트 Admin, 본인이 작성, 혹은 같은 그룹(부서/팀) 소속
    can_edit = is_system_admin or user_role == 'Admin' or issue['author_id'] == user_id or author_group == user_group_id

    if can_edit and issue['status'] in ['Pending', 'Open', 'In Progress', 'Rejected']:
        st.subheader(f"#{issue['id']} 이슈 수정 (Edit Issue)")
        with st.form("edit_issue_form"):
            new_title = st.text_input("제목 (Title)", value=issue['title'])
            new_desc = st.text_area("내용 (Description)", value=issue['description'])
            priority_options = ["Low", "Medium", "High"]
            new_priority = st.selectbox("중요도 (Priority)", priority_options, index=priority_options.index(issue['priority']))
            new_due_date = st.date_input("완료 목표일 (Due Date)", value=datetime.strptime(issue['due_date'], "%Y-%m-%d").date() if isinstance(issue['due_date'], str) else issue['due_date'])

            submit_edit = st.form_submit_button("내용 수정 저장")
            if submit_edit:
                # 이슈 내용 업데이트
                update_issue(issue_id, title=new_title, description=new_desc, priority=new_priority, due_date=new_due_date)
                # 이력 남기기
                add_revision(issue_id, user_id, "이슈 기본 내용(제목, 내용 등) 수정됨")
                st.success("수정이 완료되었습니다.")
                st.rerun()

        st.divider()

    st.header(f"#{issue['id']} - {issue['title']}")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**프로젝트:** {issue['project_name']}")
        st.write(f"**작성자:** {issue['author_name']}")
        st.write(f"**상태:** {issue['status']}")
        st.write(f"**중요도:** {issue['priority']}")
    with col2:
        st.write(f"**담당자:** {issue['assignee_name'] or '미할당 (Unassigned)'}")
        st.write(f"**목표일:** {issue['due_date']}")
        st.write(f"**작성일:** {issue['created_at']}")
        st.write(f"**수정일:** {issue['updated_at']}")

    st.subheader("내용 (Description)")
    st.write(issue['description'])

    # Reject Reason (if any)
    if issue['status'] == 'Rejected' and issue['reject_reason']:
        st.error(f"**반려 사유 (Reject Reason):** {issue['reject_reason']}")

    # Attachments
    attachments = get_attachments(issue_id)
    if attachments:
        st.subheader("첨부파일 (Attachments)")
        for att in attachments:
            st.write(f"- {att['filename']}")
            # In a real app, provide a download button/link

    st.divider()

    st.subheader("작업 (Actions)")

    # Status transitions based on role
    new_status = issue['status']
    reject_reason = ""
    assigned_to = issue['assigned_to']

    if user_role == 'Admin' and issue['status'] == 'Pending':
        col1, col2 = st.columns(2)
        with col1:
            if st.button("승인 (Approve & Open)"):
                new_status = 'Open'
        with col2:
            reject_reason_input = st.text_input("반려 사유 (Reject Reason)")
            if st.button("반려 (Reject)"):
                if not reject_reason_input:
                    st.error("반려 사유를 입력하세요.")
                else:
                    new_status = 'Rejected'
                    reject_reason = reject_reason_input

    elif user_role in ['Admin', 'Developer'] and issue['status'] in ['Open', 'In Progress', 'Resolved']:
        status_options = ['Open', 'In Progress', 'Resolved', 'Closed']
        current_index = status_options.index(issue['status']) if issue['status'] in status_options else 0
        new_status = st.selectbox("상태 변경 (Change Status)", status_options, index=current_index)

        if user_role == 'Admin':
            members = get_project_members(issue['project_id'])
            devs = [m for m in members if m['project_role'] in ['Admin', 'Developer']]
            dev_options = {m['username']: m['id'] for m in devs}
            dev_options["미할당 (Unassigned)"] = None

            current_assignee = issue['assignee_name'] if issue['assignee_name'] else "미할당 (Unassigned)"
            selected_dev = st.selectbox("담당자 할당 (Assign Developer)", list(dev_options.keys()), index=list(dev_options.keys()).index(current_assignee) if current_assignee in dev_options else 0)
            assigned_to = dev_options[selected_dev]

    # Save Changes Button
    if new_status != issue['status'] or assigned_to != issue['assigned_to']:
        if st.button("변경사항 저장 (Save Changes)"):
            update_kwargs = {'status': new_status, 'assigned_to': assigned_to}
            if new_status == 'Rejected':
                update_kwargs['reject_reason'] = reject_reason

            update_issue(issue_id, **update_kwargs)

            summary = []
            if new_status != issue['status']:
                summary.append(f"상태 변경: {issue['status']} -> {new_status}")
            if assigned_to != issue['assigned_to']:
                summary.append(f"담당자 변경")

            add_revision(issue_id, user_id, ", ".join(summary))
            st.success("변경사항이 저장되었습니다.")
            st.rerun()

    st.divider()

    # Revisions / History
    from src.ui.issue_history import render_issue_history
    render_issue_history(issue_id)

    if st.button("목록으로 돌아가기 (Back to List)"):
        st.session_state['current_view'] = 'Issue List'
        st.rerun()
