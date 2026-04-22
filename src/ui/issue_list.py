import streamlit as st
import pandas as pd
from datetime import datetime
from src.database.db import get_issues_for_user

def highlight_overdue(row):
    today = datetime.now().date()
    try:
        due_date = pd.to_datetime(row['due_date']).date()
        if due_date < today and row['status'] not in ['Resolved', 'Closed']:
            return ['background-color: #ffcccc'] * len(row)
    except:
        pass
    return [''] * len(row)

def render_issue_list():
    st.header("이슈 목록 (Issue List)")

    user_id = st.session_state.get('user_id')
    is_system_admin = st.session_state.get('is_system_admin')
    group_id = st.session_state.get('group_id')

    issues = get_issues_for_user(user_id, is_system_admin, group_id)

    if not issues:
        st.info("조회할 이슈가 없습니다.")
        return

    df = pd.DataFrame([dict(row) for row in issues])

    # Selecting relevant columns
    cols_to_show = ['id', 'project_name', 'title', 'author_name', 'status', 'priority', 'due_date', 'created_at']
    # Filter only available columns (e.g. if project_role is present for non-admins)
    available_cols = [c for c in cols_to_show if c in df.columns]

    df_display = df[available_cols].copy()

    # Styled dataframe
    st.dataframe(
        df_display.style.apply(highlight_overdue, axis=1),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("이슈 상세 보기 (View Issue Details)")
    selected_issue_id = st.number_input("조회할 이슈 ID 입력 (Enter Issue ID):", min_value=0, step=1)
    if st.button("상세 보기 (View Details)"):
        if selected_issue_id > 0:
            if selected_issue_id in df['id'].values:
                st.session_state['current_view'] = 'Issue Detail'
                st.session_state['selected_issue_id'] = selected_issue_id
                st.rerun()
            else:
                st.error("접근 권한이 없거나 존재하지 않는 이슈입니다.")
