"""
FAQ 검색 페이지
- 직접 검색 / 트렌드 키워드 선택 (둘 중 하나)
- 브랜드 필터 (기본: 전체 선택)
- company_faq 테이블 없을 시 안내 메시지
"""

import os
import streamlit as st
import pymysql
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# 설정 (.env 기준)
# ──────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "homework"),
    "password": os.getenv("DB_PASSWORD", "playdatahomework80"),
    "charset":  "utf8mb4",
    "db":       os.getenv("DB_NAME",     "car_project_db"),
}

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


# ──────────────────────────────────────────────
# DB 유틸
# ──────────────────────────────────────────────
def get_brands() -> list[str]:
    """company_faq 에서 브랜드 목록 조회"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT brand FROM company_faq ORDER BY brand")
        brands = [r[0] for r in cur.fetchall()]
        conn.close()
        return brands
    except Exception:
        return []


def fetch_faq(keywords: tuple, search_text: str, brands: tuple) -> tuple[str, list]:
    """
    FAQ 검색
    Returns: ("ok" | "no_table" | "error", rows)
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()

        conditions, params = [], []

        if search_text:
            conditions.append("(question LIKE %s OR answer LIKE %s)")
            params += [f"%{search_text}%", f"%{search_text}%"]
        elif keywords:
            for kw in keywords:
                conditions.append("(question LIKE %s OR answer LIKE %s)")
                params += [f"%{kw}%", f"%{kw}%"]

        if brands:
            ph = ",".join(["%s"] * len(brands))
            conditions.append(f"brand IN ({ph})")
            params += list(brands)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT brand, category, question, answer
            FROM company_faq {where}
            ORDER BY brand, category
            LIMIT 700
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return ("ok", rows)

    except pymysql.err.ProgrammingError as e:
        if "doesn't exist" in str(e):
            return ("no_table", [])
        return ("error", [])
    except Exception:
        return ("error", [])


def _render_pagination(total: int, current_page: int, prefix: str = "top") -> int:
    """
    페이지네이션 컨트롤 렌더링.
    버튼 클릭 시 이동할 페이지 번호를 반환, 변동 없으면 current_page 반환.
    prefix: 상단/하단 호출 시 key 중복 방지용 ("top" | "bot")
    """
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
        if st.button("◀ 이전", key=f"_pg_{prefix}_prev", disabled=(current_page == 1), use_container_width=True):
            next_page = current_page - 1

    for i, pn in enumerate(page_nums):
        with cols[i + 1]:
            btn_type = "primary" if pn == current_page else "secondary"
            if st.button(str(pn), key=f"_pg_{prefix}_{pn}", type=btn_type, use_container_width=True):
                next_page = pn

    with cols[-1]:
        if st.button("다음 ▶", key=f"_pg_{prefix}_next", disabled=(current_page == total_pages), use_container_width=True):
            next_page = current_page + 1

    return next_page


# ──────────────────────────────────────────────
# 콜백
# ──────────────────────────────────────────────
def _on_search_change(trend_keywords: list[str]):
    """검색어 입력 → 트렌드 키워드 전체 해제"""
    if st.session_state.faq_search_input:
        for kw in trend_keywords:
            st.session_state[f"kw_{kw}"] = False


def _on_keyword_change(kw: str):
    """키워드 체크 → 검색어 초기화"""
    if st.session_state[f"kw_{kw}"]:
        st.session_state.faq_search_input = ""


def _on_brand_all_change(all_brands: list[str]):
    """전체 체크박스 → 모든 브랜드 동기화"""
    val = st.session_state.brand_all_check
    for b in all_brands:
        st.session_state[f"brand_{b}"] = val


def _on_brand_change(all_brands: list[str]):
    """개별 브랜드 변경 → 전체 체크박스 동기화"""
    all_checked = all(st.session_state.get(f"brand_{b}", True) for b in all_brands)
    st.session_state.brand_all_check = all_checked


# ──────────────────────────────────────────────
# 메인 함수
# ──────────────────────────────────────────────
def show():
    # 트렌드 키워드: app.py 에서 session_state 로 넘겨주면 사용, 없으면 기본값
    trend_keywords: list[str] = st.session_state.get("trend_keywords", DEFAULT_KEYWORDS)

    # ── session_state 초기화
    if "faq_search_input" not in st.session_state:
        st.session_state.faq_search_input = ""

    # 키워드 목록이 바뀌었을 때만 체크 상태 강제 재설정 (첫 번째만 True)
    # 같은 목록이면 사용자가 수동으로 바꾼 체크 상태를 유지
    _cur_kw_list = list(trend_keywords)
    if st.session_state.get("_faq_last_keywords") != _cur_kw_list:
        st.session_state["_faq_last_keywords"] = _cur_kw_list
        for i, kw in enumerate(trend_keywords):
            st.session_state[f"kw_{kw}"] = (i == 0)
    else:
        for i, kw in enumerate(trend_keywords):
            if f"kw_{kw}" not in st.session_state:
                st.session_state[f"kw_{kw}"] = (i == 0)

    all_brands = get_brands()

    if "brand_all_check" not in st.session_state:
        st.session_state.brand_all_check = True
    for b in all_brands:
        if f"brand_{b}" not in st.session_state:
            st.session_state[f"brand_{b}"] = True

    # ══════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════
    st.title("🔍 FAQ 검색")

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
        _on_search_change(trend_keywords)

    st.caption("검색어 입력 시 트렌드 키워드 선택은 초기화됩니다.")

    st.divider()

    # ── 2. 트렌드 키워드 ──────────────────────
    st.markdown("#### 트렌드 키워드")
    st.caption("복수 선택 시 모든 키워드가 포함된 FAQ만 표시 · 키워드 선택 시 검색어는 초기화됩니다.")

    kw_cols = st.columns(4)
    for i, kw in enumerate(trend_keywords):
        with kw_cols[i % 4]:
            st.checkbox(
                kw,
                key=f"kw_{kw}",
                on_change=_on_keyword_change,
                args=(kw,),
            )

    st.divider()

    # ── 3. 브랜드 필터 ────────────────────────
    st.markdown("#### 브랜드 필터")

    if not all_brands:
        st.warning(
            "⚠️ 브랜드 데이터가 없습니다.  \n"
            "`main.py`를 실행하여 크롤링을 먼저 진행해주세요."
        )
        return

    brand_cols = st.columns(len(all_brands) + 1)
    with brand_cols[0]:
        st.checkbox(
            "전체",
            key="brand_all_check",
            on_change=_on_brand_all_change,
            args=(all_brands,),
        )
    for i, brand in enumerate(all_brands):
        with brand_cols[i + 1]:
            st.checkbox(
                brand,
                key=f"brand_{brand}",
                on_change=_on_brand_change,
                args=(all_brands,),
            )

    st.divider()

    # ── 4. 검색 실행 ──────────────────────────
    search_text    = st.session_state.faq_search_input.strip()
    sel_keywords   = tuple(kw for kw in trend_keywords if st.session_state.get(f"kw_{kw}"))
    sel_brands     = tuple(b  for b  in all_brands     if st.session_state.get(f"brand_{b}"))

    if not sel_brands:
        st.info("브랜드를 최소 1개 이상 선택해주세요.")
        return

    # 검색 모드 결정 (검색어 우선)
    if search_text:
        status, results = fetch_faq((), search_text, sel_brands)
    elif sel_keywords:
        status, results = fetch_faq(sel_keywords, "", sel_brands)
    else:
        st.info("검색어를 입력하거나 트렌드 키워드를 선택해주세요.")
        return

    # ── 5. 결과 출력 ──────────────────────────
    if status == "no_table":
        st.error(
            "❌ `company_faq` 테이블이 존재하지 않습니다.  \n"
            "`main.py`를 실행하여 크롤링을 먼저 진행해주세요."
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

    # 검색 조건이 바뀌면 페이지를 1로 리셋
    search_key = (search_text, sel_keywords, sel_brands)
    if st.session_state.get("_faq_search_key") != search_key:
        st.session_state["_faq_search_key"] = search_key
        st.session_state["_faq_page"] = 1

    current_page = st.session_state.get("_faq_page", 1)

    # ── 현재 페이지 결과 출력 ─────────────────
    start_idx   = (current_page - 1) * ITEMS_PER_PAGE
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

    # ── 페이지네이션 (하단) ───────────────────
    st.divider()
    next_page = _render_pagination(total, current_page, prefix="bot")
    if next_page != current_page:
        st.session_state["_faq_page"] = next_page
        st.rerun()


# ── 단독 실행 ──────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="FAQ 검색", page_icon="🔍", layout="wide")
    show()
