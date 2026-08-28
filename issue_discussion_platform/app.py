"""Streamlit entrypoint for the issue discussion voice experiment.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

import streamlit as st

from issue_discussion_platform.prompts import SYSTEM_PROMPT  # noqa: F401
from issue_discussion_platform.voice_agent import VoiceSession  # noqa: F401

st.title("Issue discussion")
