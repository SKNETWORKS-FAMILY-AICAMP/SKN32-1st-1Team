"""
FAQ 검색 페이지 — 모듈 버전 (통합 전용)
원본: faq_search.py  /  show() 로 노출, 독립 실행 블록 없음
"""

import re
import streamlit as st
from modules.connect_db import get_brands, fetch_faq

BRAND_COLORS = {
    "현대":    "#002C5F",
    "기아":    "#05141F",
    "BMW":     "#1C69D3",
    "포르쉐":  "#D5001C",
    "캐딜락":  "#8B7355",
    "쉐보레":  "#CC0000",
    "제네시스": "#A37E2C",
    "폭스바겐": "#001E50",
}

DEFAULT_KEYWORDS = ["전기차", "하이브리드", "충전", "AS/수리", "보증", "리콜", "연비", "구매"]

# 연료 유형명 → FAQ 검색어 확장 매핑
# 트랜드에서 넘어오는 값: "전기", "수소전기", "하이브리드(휘발유 + 전기)" 등
FUEL_TYPE_FAQ_TERMS: dict[str, list[str]] = {
    "전기":       ["전기차", "EV", "배터리", "충전"],
    "수소전기":   ["수소", "수소차", "수소전기", "연료전지", "FCEV"],
    "수소":       ["수소", "수소차", "연료전지", "FCEV"],
    "하이브리드": ["하이브리드", "HEV", "PHEV", "플러그인"],
    "휘발유":     ["휘발유", "가솔린"],
    "경유":       ["경유", "디젤"],
    "LPG":        ["LPG", "액화석유"],
}


def _normalize_fuel_label(raw: str) -> str:
    """'하이브리드(휘발유 + 전기)' → '하이브리드'"""
    return re.sub(r"\s*\(.*?\)", "", raw).strip()


def _expand_faq_keywords(raw: str) -> list[str]:
    """연료 유형명을 FAQ 검색용 동의어 목록으로 변환. 매핑 없으면 정규화된 라벨 그대로 반환."""
    label = _normalize_fuel_label(raw)
    return FUEL_TYPE_FAQ_TERMS.get(label, [label])


# ──────────────────────────────────────────────
# DB 유틸
# ──────────────────────────────────────────────
def _render_pagination(total: int, current_page: int, prefix: str = "top") -> int:
    ITEMS_PER_PAGE = 10
    PAGE_GROUP_SIZE = 5

    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    current_page = min(current_page, total_pages)

    group_start = ((current_page - 1) // PAGE_GROUP_SIZE) * PAGE_GROUP_SIZE + 1
    group_end   = min(group_start + PAGE_GROUP_SIZE - 1, total_pages)
    page_nums   = list(range(group_start, group_end + 1))

    next_page = current_page
    cols = st.columns([1.2] + [0.8] * len(page_nums) + [1.2])

    with cols[0]:
        if st.button("이전", key=f"_pg_{prefix}_prev", disabled=(current_page == 1), use_container_width=True):
            next_page = current_page - 1

    for i, pn in enumerate(page_nums):
        with cols[i + 1]:
            btn_type = "primary" if pn == current_page else "secondary"
            if st.button(str(pn), key=f"_pg_{prefix}_{pn}", type=btn_type, use_container_width=True):
                next_page = pn

    with cols[-1]:
        if st.button("다음", key=f"_pg_{prefix}_next", disabled=(current_page == total_pages), use_container_width=True):
            next_page = current_page + 1

    return next_page


# ──────────────────────────────────────────────
# 메인 함수
# ──────────────────────────────────────────────
def show():
    trend_keywords: list[str] = st.session_state.get("trend_keywords", DEFAULT_KEYWORDS)

    if "faq_search_input" not in st.session_state:
        st.session_state.faq_search_input = ""

    # 키워드 목록이 바뀌었을 때만 pills 선택 상태 재설정 (첫 번째만 선택)
    # pills 옵션이 정규화된 라벨이므로 초기값도 정규화된 라벨로 설정
    _cur_kw_list = list(trend_keywords)
    if st.session_state.get("_faq_last_keywords") != _cur_kw_list:
        st.session_state["_faq_last_keywords"] = _cur_kw_list
        first_label = [_normalize_fuel_label(trend_keywords[0])] if trend_keywords else []
        st.session_state["faq_keyword_pills"] = first_label

    all_brands = get_brands()
    _BRAND_ALL = "전체"
    _brand_pill_options = [_BRAND_ALL] + all_brands

    if st.session_state.get("_faq_last_brands") != all_brands:
        st.session_state["_faq_last_brands"] = all_brands
        st.session_state["faq_brand_pills"] = [_BRAND_ALL] + all_brands
        st.session_state["_faq_brand_prev"] = [_BRAND_ALL] + all_brands

    st.title("FAQ 검색")

    # ── 1. 검색창 ─────────────────────────────
    st.markdown("#### 직접 검색")
    col_input, col_btn = st.columns([6, 1])
    with col_input:
        st.text_input(
            "검색창",
            key="faq_search_input",
            placeholder="검색어를 입력하고 검색 버튼을 누르세요...",
            label_visibility="collapsed",
        )
    with col_btn:
        search_clicked = st.button("검색", use_container_width=True)

    if search_clicked and st.session_state.faq_search_input:
        st.session_state["faq_keyword_pills"] = []

    st.caption("검색어 입력 시 트렌드 키워드 선택은 초기화됩니다.")
    st.divider()

    # ── 2. 트렌드 키워드 ──────────────────────
    st.markdown("#### 트렌드 키워드")
    st.caption("복수 선택 시 모든 키워드가 포함된 FAQ만 표시됩니다.")

    sel_keywords = st.pills(
        "트렌드 키워드 선택",
        [_normalize_fuel_label(kw) for kw in trend_keywords],
        selection_mode="multi",
        key="faq_keyword_pills",
        label_visibility="collapsed",
    ) or []

    st.divider()

    # ── 3. 브랜드 필터 ────────────────────────
    st.markdown("#### 브랜드 필터")

    if not all_brands:
        st.warning(
            "브랜드 데이터가 없습니다.  \n"
            "`crawler/Crawlermain.py`를 실행하여 크롤링을 먼저 진행해주세요."
        )
        return

    # 전체 버튼 토글 동기화
    _curr = set(st.session_state.get("faq_brand_pills", []))
    _prev = set(st.session_state.get("_faq_brand_prev", _curr))
    _prev_had_all = _BRAND_ALL in _prev
    _curr_has_all = _BRAND_ALL in _curr

    if _curr_has_all and not _prev_had_all:
        # 전체 새로 선택 → 모두 선택
        st.session_state["faq_brand_pills"] = [_BRAND_ALL] + all_brands
    elif not _curr_has_all and _prev_had_all:
        # 전체 해제 → 모두 해제
        st.session_state["faq_brand_pills"] = []
    else:
        # 개별 브랜드 변경 → 전체 버튼 자동 동기화
        _all_selected = all(b in _curr for b in all_brands)
        if _all_selected and _BRAND_ALL not in _curr:
            st.session_state["faq_brand_pills"] = [_BRAND_ALL] + all_brands
        elif not _all_selected and _BRAND_ALL in _curr:
            st.session_state["faq_brand_pills"] = [b for b in _curr if b != _BRAND_ALL]

    st.session_state["_faq_brand_prev"] = list(st.session_state.get("faq_brand_pills", []))

    sel_brands_raw = st.pills(
        "브랜드 선택",
        _brand_pill_options,
        selection_mode="multi",
        key="faq_brand_pills",
        label_visibility="collapsed",
    ) or []

    st.divider()

    # ── 4. 검색 실행 ──────────────────────────
    search_text  = st.session_state.faq_search_input.strip()
    # pills는 정규화된 라벨을 반환하므로 원본 keyword 목록에서 매핑
    label_to_raw = {_normalize_fuel_label(kw): kw for kw in trend_keywords}
    sel_keywords_raw = tuple(label_to_raw.get(lbl, lbl) for lbl in sel_keywords)
    sel_brands   = tuple(b for b in sel_brands_raw if b != _BRAND_ALL)

    if not sel_brands:
        st.info("브랜드를 최소 1개 이상 선택해주세요.")
        return

    if search_text:
        # 연료명인 경우 동의어 확장 적용 (trend_dashboard 셀 클릭으로 넘어온 경우)
        expanded = _expand_faq_keywords(search_text)
        if len(expanded) > 1 or expanded[0] != search_text:
            kw_groups = (tuple(expanded),)
            status, results = fetch_faq((), "", sel_brands, keyword_groups=kw_groups)
        else:
            status, results = fetch_faq((), search_text, sel_brands)
    elif sel_keywords_raw:
        # 각 연료 유형을 FAQ 동의어로 확장 후 OR 그룹으로 검색
        kw_groups = tuple(tuple(_expand_faq_keywords(kw)) for kw in sel_keywords_raw)
        status, results = fetch_faq((), "", sel_brands, keyword_groups=kw_groups)
    else:
        st.info("검색어를 입력하거나 트렌드 키워드를 선택해주세요.")
        return

    # ── 5. 결과 출력 ──────────────────────────
    if status == "no_table":
        st.error(
            "❌ `company_faq` 테이블이 존재하지 않습니다.  \n"
            "`crawler/Crawlermain.py`를 실행하여 크롤링을 먼저 진행해주세요."
        )
        return

    if status == "error":
        st.error("DB 연결 중 오류가 발생했습니다.")
        return

    if not results:
        st.info("검색 결과가 없습니다.")
        return

    ITEMS_PER_PAGE = 10
    total = len(results)
    st.markdown(f"**검색결과 {total}건**")

    search_key = (search_text, sel_keywords, sel_brands)
    if st.session_state.get("_faq_search_key") != search_key:
        st.session_state["_faq_search_key"] = search_key
        st.session_state["_faq_page"] = 1

    current_page = st.session_state.get("_faq_page", 1)

    start_idx    = (current_page - 1) * ITEMS_PER_PAGE
    page_results = results[start_idx : start_idx + ITEMS_PER_PAGE]
    st.caption(f"{start_idx + 1}–{start_idx + len(page_results)} / {total}건")

    for brand, category, question, answer in page_results:
        color = BRAND_COLORS.get(brand, "#555555")
        badge = (
            f'<span style="background:{color};color:#fff;'
            f'padding:2px 10px;border-radius:4px;'
            f'font-size:12px;font-weight:bold">{brand}</span>'
            f'&nbsp;&nbsp;<span style="color:#888;font-size:13px">{category or ""}</span>'
        )
        with st.expander(question):
            st.markdown(badge, unsafe_allow_html=True)
            st.markdown("---")
            st.write(answer if answer else "(답변 없음)")

    st.divider()
    next_page = _render_pagination(total, current_page, prefix="bot")
    if next_page != current_page:
        st.session_state["_faq_page"] = next_page
        st.rerun()