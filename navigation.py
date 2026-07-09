"""
Navigation helpers.

The current app still runs through legacy/runtime.py. These functions are the
target home for navigation code as the next refactor phase.
"""

import streamlit as st
from .config import ALL_PAGES, PAGE_LABELS

def route_to(page_name: str) -> None:
    if page_name not in ALL_PAGES:
        page_name = "Home"
    st.session_state.pending_page = page_name
    st.session_state.active_page = page_name
    st.session_state["_nav_initialised"] = True
    st.session_state["single_working_navigation"] = PAGE_LABELS.get(page_name, page_name)
    try:
        st.query_params["nav"] = page_name
    except Exception:
        pass
    st.rerun()

def route_button(label: str, page_name: str, key: str, help_text: str | None = None, type: str = "secondary"):
    return st.button(
        label,
        key=key,
        help=help_text,
        type=type,
        use_container_width=True,
        on_click=route_to,
        args=(page_name,),
    )
