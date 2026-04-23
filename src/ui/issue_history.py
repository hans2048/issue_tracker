import streamlit as st
import json
from src.database.db import get_revisions

def render_issue_history(issue_id):
    st.subheader("이슈 이력 (Revision History)")
    revisions = get_revisions(issue_id)
    if revisions:
        for rev in revisions:
            rev_no = rev.get('revision_no', '')
            rev_no_str = f"[{rev_no}] " if rev_no else ""
            st.markdown(f"**{rev_no_str}{rev['modified_at']}** - {rev['modified_by_name']}: {rev['change_summary']}")
            if rev.get('new_content'):
                with st.expander("상세 데이터 보기 (View Full Revision Data)"):
                    try:
                        parsed = json.loads(rev['new_content'])
                        st.json(parsed)
                    except:
                        st.write(rev['new_content'])
    else:
        st.write("이력이 없습니다.")
