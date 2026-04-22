import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.database.db import get_issues_for_user

def render_dashboard():
    st.header("대시보드 (Dashboard)")

    user_id = st.session_state.get('user_id')
    is_system_admin = st.session_state.get('is_system_admin')
    group_id = st.session_state.get('group_id')

    issues = get_issues_for_user(user_id, is_system_admin, group_id)

    if not issues:
        st.info("조회할 이슈가 없습니다.")
        return

    df = pd.DataFrame([dict(row) for row in issues])

    # Calculate overdue
    today = datetime.now().date()
    df['due_date'] = pd.to_datetime(df['due_date']).dt.date
    df['is_overdue'] = (df['due_date'] < today) & (~df['status'].isin(['Resolved', 'Closed']))

    # Overdue highlighting (red metric)
    overdue_count = df['is_overdue'].sum()

    st.subheader("요약 (Summary)")
    col1, col2, col3 = st.columns(3)
    col1.metric("총 이슈 (Total Issues)", len(df))
    col2.metric("진행 중 (In Progress)", len(df[df['status'] == 'In Progress']))

    if overdue_count > 0:
        col3.markdown(f"<div style='padding: 1rem; border-radius: 0.5rem; background-color: #ffcccc; color: red;'>지연 항목 (Overdue): <b>{overdue_count}</b></div>", unsafe_allow_html=True)
    else:
        col3.metric("지연 항목 (Overdue)", overdue_count)

    # Issue Status Chart
    st.subheader("상태별 이슈 현황 (Issues by Status)")
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    fig1 = px.pie(status_counts, names='status', values='count', title='이슈 상태 비율 (Issue Status Ratio)')
    st.plotly_chart(fig1)

    # Overdue list
    if overdue_count > 0:
        st.subheader("🚨 지연 항목 목록 (Overdue List)")
        overdue_df = df[df['is_overdue']][['id', 'project_name', 'title', 'status', 'due_date']]
        st.dataframe(overdue_df.style.applymap(lambda x: "background-color: #ffcccc", subset=['due_date']))
