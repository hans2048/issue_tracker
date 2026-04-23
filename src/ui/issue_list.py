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

    # Add attachment indicator
    if 'attachment_count' in df.columns:
        df['첨부파일'] = df['attachment_count'].apply(lambda x: '📎' if x > 0 else '')
    else:
        df['첨부파일'] = ''

    # Selecting relevant columns
    cols_to_show = ['id', 'project_name', 'title', 'author_name', 'status', 'priority', 'due_date', '첨부파일', 'created_at']
    # Filter only available columns (e.g. if project_role is present for non-admins)
    available_cols = [c for c in cols_to_show if c in df.columns]

    df_display = df[available_cols].copy()

    # Styled dataframe with selection
    st.write("표의 행을 선택하여 이슈 상세정보를 확인할 수 있습니다.")

    # We use Streamlit's new st.dataframe selection feature
    event = st.dataframe(
        df_display.style.apply(highlight_overdue, axis=1),
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun"
    )

    # When a row is selected via click, store it in session state so the button click doesn't lose it
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        st.session_state['temp_selected_issue_id'] = df_display.iloc[selected_index]['id']
        st.session_state['temp_selected_issue_title'] = df_display.iloc[selected_index]['title']
    else:
        if 'temp_selected_issue_id' in st.session_state:
            del st.session_state['temp_selected_issue_id']
            del st.session_state['temp_selected_issue_title']

    if 'temp_selected_issue_id' in st.session_state:
        issue_id = st.session_state['temp_selected_issue_id']
        issue_title = st.session_state['temp_selected_issue_title']

        st.success(f"선택된 이슈: #{issue_id} - {issue_title}")

        def view_details():
            st.session_state['current_view'] = 'Issue Detail'
            st.session_state['selected_issue_id'] = st.session_state['temp_selected_issue_id']

        st.button("상세 보기 (View Details)", type="primary", on_click=view_details)
