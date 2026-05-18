"""
소나기 팀 | 자동차 통합 대시보드
  - 🚗 트렌드 대시보드  (app.py 기반)
  - 🔍 FAQ 검색         (faq_search.py 기반)
  - 📊 통계 분석        (app3.py 기반) — 클릭 시 아코디언으로 5개 모듈 표시
"""

import streamlit as st

st.set_page_config(
    page_title="소나기 팀 | 자동차 대시보드",
    page_icon="🚘",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --blue-950: #0f2f55;
        --blue-800: #174f84;
        --blue-600: #2477bd;
        --line: #cfe4f7;
    }

    /* Streamlit 자동 다중 페이지 네비게이션 숨김 */
    [data-testid="stSidebarNav"] { display: none !important; }

    .stApp {
        background: linear-gradient(180deg, #f6fbff 0%, #eef7ff 42%, #ffffff 100%);
        color: #17324d;
    }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--blue-950); }

    section[data-testid="stSidebar"] {
        background: #eef7ff;
        border-right: 1px solid var(--line);
    }

    /* 사이드바 일반 버튼 */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1px solid var(--line) !important;
        color: #17324d !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #dff3ff !important;
        border-color: var(--blue-600) !important;
    }

    /* 사이드바 활성 버튼 */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: var(--blue-600) !important;
        border: 1px solid var(--blue-800) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    /* 아코디언 (expander) 헤더 스타일 */
    section[data-testid="stSidebar"] details summary {
        background-color: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.45rem 0.75rem;
        font-weight: 600;
        color: #17324d;
        cursor: pointer;
    }
    section[data-testid="stSidebar"] details[open] summary {
        background-color: #dff3ff;
        border-color: var(--blue-600);
        color: var(--blue-950);
        border-radius: 8px 8px 0 0;
    }
    section[data-testid="stSidebar"] details summary:hover {
        background-color: #dff3ff;
        border-color: var(--blue-600);
    }

    /* 아코디언 내부 리스트 영역 */
    section[data-testid="stSidebar"] details > div {
        border: 1px solid var(--line);
        border-top: none;
        border-radius: 0 0 8px 8px;
        background-color: #f8fcff;
        padding: 0.3rem 0.4rem 0.4rem 0.4rem;
    }

    /* 아코디언 내부 버튼 (리스트 항목) */
    section[data-testid="stSidebar"] details button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        border-radius: 6px !important;
        color: #315a7c !important;
        font-size: 0.88rem !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 0.3rem 0.6rem !important;
    }
    section[data-testid="stSidebar"] details button[kind="secondary"]:hover {
        background-color: #dff3ff !important;
        color: var(--blue-950) !important;
    }
    section[data-testid="stSidebar"] details button[kind="primary"] {
        background-color: #dff3ff !important;
        border: 1px solid var(--blue-600) !important;
        color: var(--blue-950) !important;
        border-radius: 6px !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 8px 22px rgba(20, 76, 123, 0.07);
    }
    hr { border-color: var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── session_state 초기화 ───────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "trend"
if "model" not in st.session_state:
    st.session_state.model = "1. 연식 차량 대수 조회"

from modules.stats_dashboard import MODELS


# ── 사이드바 ──────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#0f2f55; font-size:1.2rem; margin-bottom:0.2rem;'>🚘 소나기 팀</h2>"
            "<p style='color:#6a8fa8; font-size:0.82rem; margin-top:0; margin-bottom:1rem;'>"
            "자동차 통합 대시보드</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.session_state.page

        # ── 트렌드 대시보드 버튼 ─────────────────────────────
        if st.button(
            "🚗  트렌드 대시보드",
            use_container_width=True,
            type="primary" if page == "trend" else "secondary",
            key="btn_trend",
        ):
            st.session_state.page = "trend"
            st.rerun()

        # ── FAQ 검색 버튼 ────────────────────────────────────
        if st.button(
            "🔍  FAQ 검색",
            use_container_width=True,
            type="primary" if page == "faq" else "secondary",
            key="btn_faq",
        ):
            st.session_state.page = "faq"
            st.rerun()

        # ── 통계 분석 아코디언 ───────────────────────────────
        # 통계 탭이 활성이면 자동으로 펼쳐진 상태로 표시
        with st.expander("📊  통계 분석", expanded=(page == "stats")):
            for m in MODELS:
                is_active = (page == "stats") and (st.session_state.model == m)
                if st.button(
                    f"{'▶ ' if is_active else '　 '}{m}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    key=f"btn_model_{m}",
                ):
                    st.session_state.page = "stats"
                    st.session_state.model = m
                    st.rerun()


render_sidebar()

# ── 메인 콘텐츠 ───────────────────────────────────────────────
page = st.session_state.page

if page == "trend":
    from modules.trend_dashboard import show as show_trend
    show_trend()

elif page == "faq":
    from modules.faq_search import show as show_faq
    show_faq()

elif page == "stats":
    from modules.stats_dashboard import render as render_stats
    render_stats(st.session_state.model)
