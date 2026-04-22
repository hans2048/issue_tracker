import streamlit as st
import pandas as pd
from src.database.db import get_unread_notices_for_user, mark_notice_read, get_all_notices

@st.dialog("공지사항 (Notice)")
def render_notice_popup(notice):
    st.write(f"**{notice['title']}**")
    st.write(notice['content'])
    st.write(f"*(작성일: {notice['created_at']})*")

    st.divider()
    if st.button("다시 보지 않기 (Do not show again)", key=f"hide_notice_{notice['id']}"):
        user_id = st.session_state.get('user_id')
        mark_notice_read(user_id, notice['id'])
        st.session_state[f'notice_shown_{notice["id"]}'] = True
        st.rerun()

def check_and_show_notices():
    user_id = st.session_state.get('user_id')
    if not user_id:
        return

    unread_notices = get_unread_notices_for_user(user_id)
    for notice in unread_notices:
        # Check session state so we don't open multiple dialogs instantly or get stuck in a loop
        if not st.session_state.get(f'notice_shown_{notice["id"]}', False):
            st.session_state[f'notice_shown_{notice["id"]}'] = True
            render_notice_popup(notice)
            break # Show one at a time

def render_notice_history():
    st.header("공지사항 목록 (Notices)")
    notices = get_all_notices()

    if not notices:
        st.info("등록된 공지사항이 없습니다.")
        return

    df = pd.DataFrame([dict(n) for n in notices])
    df['상태'] = df['is_active'].map({1: '활성 (Active)', 0: '비활성 (Inactive)'})

    # We only show active notices to normal users, but for history we can show all or just active.
    # Let's show active ones for everyone, system admins can see inactive ones too if needed.
    is_system_admin = st.session_state.get('is_system_admin')
    if not is_system_admin:
        df = df[df['is_active'] == 1]

    if df.empty:
        st.info("등록된 공지사항이 없습니다.")
        return

    cols_to_show = ['id', 'title', 'content', 'author_name', 'created_at']
    if is_system_admin:
        cols_to_show.append('상태')

    st.dataframe(df[cols_to_show], hide_index=True, use_container_width=True)
