"""
소나기 팀 | 자동차 통합 대시보드
  - 트렌드 대시보드  (app.py 기반)
  - FAQ 검색         (faq_search.py 기반)
  - 통계 분석        (app3.py 기반) — 클릭 시 아코디언으로 5개 모듈 표시
"""

import streamlit as st

st.set_page_config(
    page_title="소나기 팀 | 자동차 대시보드",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --blue-950: #0f2f55;
        --blue-800: #174f84;
        --blue-600: #2477bd;
        --blue-500: #2f91d8;
        --blue-100: #dff3ff;
        --blue-75: #eaf8ff;
        --blue-50: #f6fbff;
        --line: #cfe4f7;
        --sidebar-line: #9bc9e8;
        --text: #17324d;
        --muted: #5f7f99;
    }

    /* Streamlit 자동 다중 페이지 네비게이션 숨김 */
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    .stApp {
        background: linear-gradient(180deg, #f6fbff 0%, #eef7ff 42%, #ffffff 100%);
        color: var(--text);
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
        border: 1px solid var(--sidebar-line) !important;
        color: var(--text) !important;
        border-radius: 8px !important;
        min-height: 2.55rem !important;
        font-weight: 500 !important;
        position: relative !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: var(--blue-100) !important;
        border-color: var(--blue-600) !important;
    }

    /* 사이드바 활성 버튼 */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(180deg, #41a5e6 0%, var(--blue-500) 100%) !important;
        border: 1px solid var(--sidebar-line) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        min-height: 2.55rem !important;
        font-weight: 550 !important;
        position: relative !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        background: linear-gradient(180deg, #55b4ed 0%, #359be0 100%) !important;
        border-color: var(--sidebar-line) !important;
    }
    section[data-testid="stSidebar"] button p {
        width: 100%;
        text-align: center;
        font-size: 1rem;
        font-weight: 500;
    }

    /* 아코디언 (expander) 헤더 스타일 */
    section[data-testid="stSidebar"] details summary {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #ffffff;
        border: 1px solid var(--blue-500);
        border-radius: 8px;
        min-height: 2.55rem;
        padding: 0.45rem 0.75rem;
        font-size: 1rem;
        font-weight: 500;
        color: var(--text);
        cursor: pointer;
        text-align: center;
        position: relative;
        list-style: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] details {
        border: 0 !important;
    }
    section[data-testid="stSidebar"] details > summary {
        outline: 0 !important;
    }
    section[data-testid="stSidebar"] details summary > span {
        width: 100% !important;
        padding-right: 0 !important;
    }
    section[data-testid="stSidebar"] details summary [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
    }
    section[data-testid="stSidebar"] details summary p {
        width: 100%;
        text-align: center;
        font-size: 1rem;
        font-weight: 500;
    }
    /* Material Icons 아이콘 + 직접 부모 span만 숨김 */
    section[data-testid="stSidebar"] details summary [data-testid="stIconMaterial"],
    section[data-testid="stSidebar"] details summary span:has(> [data-testid="stIconMaterial"]) {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
        pointer-events: none !important;
    }
    section[data-testid="stSidebar"] details summary::after {
        content: "";
        position: absolute;
        right: 1.05rem;
        top: 50%;
        width: 0.42rem;
        height: 0.42rem;
        border: solid var(--blue-950);
        border-width: 0 1.5px 1.5px 0;
        transform: translateY(-62%) rotate(45deg);
        transform-origin: center;
        pointer-events: none;
        background: transparent;
        box-shadow: none;
    }
    section[data-testid="stSidebar"] details[open] summary::after {
        transform: translateY(-35%) rotate(-135deg);
    }
    section[data-testid="stSidebar"] details summary:focus,
    section[data-testid="stSidebar"] details summary:focus-visible,
    section[data-testid="stSidebar"] details summary:active {
        outline: none !important;
        box-shadow: none !important;
        border-color: var(--blue-500) !important;
    }
    section[data-testid="stSidebar"] details summary *,
    section[data-testid="stSidebar"] details summary *:hover,
    section[data-testid="stSidebar"] details summary *:focus,
    section[data-testid="stSidebar"] details summary *:focus-visible,
    section[data-testid="stSidebar"] details summary *:active {
        outline: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] details summary::-webkit-details-marker {
        display: none !important;
    }
    section[data-testid="stSidebar"] details[open] summary {
        background: #ffffff;
        border-color: var(--blue-500);
        color: var(--blue-950);
        border-radius: 8px 8px 0 0;
    }
    section[data-testid="stSidebar"] details summary:hover {
        background-color: var(--blue-100);
        border-color: var(--sidebar-line);
    }
    section[data-testid="stSidebar"] details summary:hover *,
    section[data-testid="stSidebar"] details summary:hover p,
    section[data-testid="stSidebar"] details summary:focus *,
    section[data-testid="stSidebar"] details summary:focus p,
    section[data-testid="stSidebar"] details summary:active *,
    section[data-testid="stSidebar"] details summary:active p {
        color: var(--blue-950) !important;
        text-decoration-color: var(--blue-950) !important;
    }

    /* 아코디언 내부 리스트 영역 */
    section[data-testid="stSidebar"] details > div {
        border: 1px solid var(--blue-500);
        border-top: none;
        border-radius: 0 0 8px 8px;
        background-color: #ffffff;
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
    section[data-testid="stSidebar"] details button[kind="secondary"] p {
        font-size: 0.88rem !important;
        font-weight: 400 !important;
        text-align: left !important;
    }
    section[data-testid="stSidebar"] details button[kind="secondary"]:hover {
        background-color: var(--blue-100) !important;
        color: var(--blue-950) !important;
    }
    section[data-testid="stSidebar"] details button[kind="secondary"]:hover *,
    section[data-testid="stSidebar"] details button[kind="secondary"]:hover p,
    section[data-testid="stSidebar"] details button[kind="secondary"]:focus *,
    section[data-testid="stSidebar"] details button[kind="secondary"]:focus p,
    section[data-testid="stSidebar"] details button[kind="secondary"]:active *,
    section[data-testid="stSidebar"] details button[kind="secondary"]:active p {
        color: var(--blue-950) !important;
        text-decoration-color: var(--blue-950) !important;
    }
    section[data-testid="stSidebar"] details button[kind="primary"] {
        background-color: var(--blue-100) !important;
        border: 1px solid var(--blue-600) !important;
        color: var(--blue-950) !important;
        border-radius: 6px !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] details button[kind="primary"] p {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        text-align: left !important;
    }
    section[data-testid="stSidebar"] details button[kind="primary"]:hover,
    section[data-testid="stSidebar"] details button[kind="primary"]:focus,
    section[data-testid="stSidebar"] details button[kind="primary"]:active {
        background-color: var(--blue-75) !important;
        border-color: var(--blue-600) !important;
        color: var(--blue-950) !important;
    }
    section[data-testid="stSidebar"] details button[kind="primary"]:hover *,
    section[data-testid="stSidebar"] details button[kind="primary"]:hover p,
    section[data-testid="stSidebar"] details button[kind="primary"]:focus *,
    section[data-testid="stSidebar"] details button[kind="primary"]:focus p,
    section[data-testid="stSidebar"] details button[kind="primary"]:active *,
    section[data-testid="stSidebar"] details button[kind="primary"]:active p {
        color: var(--blue-950) !important;
        text-decoration-color: var(--blue-950) !important;
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

    /* 위젯 색상 대시보드 팔레트로 통일 */
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label p,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label p,
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stSlider"] label {
        color: var(--blue-950) !important;
        font-weight: 500 !important;
    }
    [data-baseweb="radio"] > div:first-child {
        border-color: var(--blue-800) !important;
        background-color: #ffffff !important;
    }
    [data-baseweb="radio"] > div:first-child > div {
        background-color: var(--blue-800) !important;
    }
    [data-baseweb="checkbox"] svg,
    [data-testid="stCheckbox"] svg {
        color: var(--blue-600) !important;
        fill: var(--blue-600) !important;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div {
        border-color: var(--line) !important;
        background-color: #ffffff !important;
    }
    [data-testid="stTextInput"] > div,
    [data-testid="stTextInput"] [data-baseweb="input"] {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        border-radius: 999px !important;
        overflow: visible !important;
    }
    [data-testid="stTextInput"] [data-baseweb="input"] > div {
        min-height: 2.6rem;
        border-radius: 999px !important;
        border: 1px solid #b9d8ef !important;
        background-color: #ffffff !important;
        box-shadow: 0 6px 16px rgba(47, 145, 216, 0.05);
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='19' height='19' viewBox='0 0 24 24' fill='none' stroke='%238a99a6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='7'%3E%3C/circle%3E%3Cpath d='m20 20-3.6-3.6'%3E%3C/path%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: 1.02rem 50% !important;
        background-size: 1.05rem 1.05rem !important;
    }
    [data-testid="stTextInput"] input {
        padding-left: 2.35rem !important;
        color: var(--text) !important;
        background: transparent !important;
    }
    [data-testid="stTextInput"]:focus-within [data-baseweb="input"] > div {
        border-color: var(--blue-500) !important;
        box-shadow: 0 0 0 3px rgba(47, 145, 216, 0.13);
    }
    [data-baseweb="select"] [aria-selected="true"] {
        background-color: var(--blue-100) !important;
        color: var(--blue-950) !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
        background-color: #ffffff !important;
        border-color: var(--blue-800) !important;
        box-shadow: 0 0 0 3px rgba(36, 119, 189, 0.16) !important;
    }
    [data-testid="stSlider"] [data-baseweb="slider"] {
        accent-color: var(--blue-500) !important;
    }
    [data-testid="stBaseButton-pills"],
    [data-testid="stBaseButton-pills"] p {
        color: var(--blue-800) !important;
    }
    [data-testid="stBaseButton-pills"] {
        background-color: #ffffff !important;
        border-color: var(--line) !important;
    }
    [data-testid="stBaseButton-pillsActive"],
    [data-testid="stBaseButton-pillsActive"] p {
        color: var(--blue-950) !important;
        font-weight: 500 !important;
    }
    [data-testid="stBaseButton-pillsActive"] {
        background-color: var(--blue-100) !important;
        border-color: var(--blue-600) !important;
    }
    [data-baseweb="tab-highlight"] {
        background-color: var(--blue-600) !important;
    }
    [data-testid="stTab"],
    [data-testid="stTab"] p,
    [data-baseweb="tab"] p {
        color: var(--blue-800) !important;
        font-weight: 500 !important;
    }
    [data-testid="stTab"][aria-selected="true"],
    [data-testid="stTab"][aria-selected="true"] p,
    [data-baseweb="tab"][aria-selected="true"] p {
        color: var(--blue-950) !important;
        font-weight: 550 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── session_state 초기화 ───────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "trend"
if "model" not in st.session_state:
    st.session_state.model = "연식 차량 대수 조회"

from modules.stats_dashboard import MODELS

# 이전 버전 번호 prefix 붙은 모델명 마이그레이션
_OLD_MODEL_LABELS = {
    "1. 연식 차량 대수 조회":      "연식 차량 대수 조회",
    "2. 연료/배기량별 차량등록 수": "연료/배기량별 차량등록 수",
    "3. 성별·연령별 등록 추이":     "성별·연령별 등록 추이",
    "4. 연간 자동차 등록 추이":     "연간 자동차 등록 추이",
    "5. 지역별 등록 증감 순위":     "지역별 등록 증감 순위",
}
if st.session_state.model in _OLD_MODEL_LABELS:
    st.session_state.model = _OLD_MODEL_LABELS[st.session_state.model]


# ── 사이드바 ──────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#0f2f55; font-size:1.48rem; margin-bottom:0.32rem;'>SKN32기 1팀</h2>"
            "<p style='color:#5f7f99; font-size:0.92rem; margin-top:0; margin-bottom:0.22rem;'>"
            "팀명: 소나기</p>"
            "<p style='color:#5f7f99; font-size:0.92rem; margin-top:0; margin-bottom:1.15rem;'>"
            "자동차 통합 대시보드</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.session_state.page

        # ── 트렌드 대시보드 버튼 ─────────────────────────────
        if st.button(
            "트렌드 대시보드",
            use_container_width=True,
            type="primary" if page == "trend" else "secondary",
            key="btn_trend",
        ):
            st.session_state.page = "trend"
            st.rerun()

        # ── FAQ 검색 버튼 ────────────────────────────────────
        if st.button(
            "FAQ 검색",
            use_container_width=True,
            type="primary" if page == "faq" else "secondary",
            key="btn_faq",
        ):
            st.session_state.page = "faq"
            st.rerun()

        # ── 통계 분석 아코디언 ───────────────────────────────
        with st.expander("통계 분석", expanded=(page == "stats")):
            for m in MODELS:
                is_active = (page == "stats") and (st.session_state.model == m)
                if st.button(
                    m,
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