"""
전국 자동차 등록 현황 트렌드 대시보드
소나기 팀 | 2026
"""

import os
import pymysql
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 설정
# ============================================================
st.set_page_config(
    page_title="자동차 트렌드 대시보드",
    page_icon="🚗",
    layout="wide",
)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "homework"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db":       os.getenv("DB_NAME", "sknmainproject1_db"),
    "charset":  "utf8mb4",
}

TREND_COLOR = {"UP": "#2ecc71", "DOWN": "#e74c3c", "FLAT": "#95a5a6"}


# ============================================================
# DB 유틸
# ============================================================
def _init_session(cur, period: int):
    cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("SET SESSION sql_mode = CONCAT(@@sql_mode, ',NO_UNSIGNED_SUBTRACTION')")
    cur.execute("SET @latest_ym = (SELECT MAX(year_months) FROM load_history)")
    cur.execute("SET @start_ym  = (SELECT MIN(year_months) FROM load_history)")
    cur.execute(f"SET @period = {period}")
    cur.execute("""
        SET @period_start_ym = DATE_FORMAT(
            DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),
                     INTERVAL @period MONTH), '%Y%m')
    """)


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str, period: int = 12) -> pd.DataFrame:
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            _init_session(cur, period)
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_summary(period: int) -> dict:
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            _init_session(cur, period)
            cur.execute("""
                SELECT
                    (SELECT MAX(year_months) FROM load_history)            AS latest_ym,
                    (SELECT COUNT(DISTINCT year_months) FROM load_history) AS total_months,
                    (SELECT cnt_total FROM car_region_stats
                     WHERE year_months = @latest_ym
                       AND region='합계' AND car_type='합계')              AS total_registered,
                    (SELECT registered_count FROM car_fuel_stats
                     WHERE year_months = @latest_ym AND fuel_type='전기'
                       AND car_type='소계' AND usage_type='계'
                       AND region='합계')                                  AS ev_total,
                    (SELECT SUM(registered_count) FROM car_fuel_stats
                     WHERE year_months = @latest_ym
                       AND fuel_type LIKE '하이브리드%'
                       AND car_type='소계' AND usage_type='계'
                       AND region='합계')                                  AS hybrid_total,
                    (SELECT registered_count FROM car_type_detail_stats
                     WHERE year_months = @latest_ym AND car_type='승용'
                       AND car_subtype='다목적' AND region='합계')         AS suv_total
            """)
            row = cur.fetchone()
            keys = ["latest_ym", "total_months", "total_registered",
                    "ev_total", "hybrid_total", "suv_total"]
            return dict(zip(keys, row))
    finally:
        conn.close()


# ============================================================
# SQL 정의
# ============================================================
SQL = {
    # 연료별
    "M1": """
        SELECT year_months, fuel_type, registered_count,
            registered_count - LAG(registered_count)
                OVER (PARTITION BY fuel_type ORDER BY year_months) AS mom_diff,
            ROUND((registered_count
                   - LAG(registered_count)
                     OVER (PARTITION BY fuel_type ORDER BY year_months))
                  / NULLIF(LAG(registered_count)
                     OVER (PARTITION BY fuel_type ORDER BY year_months),0)*100,2) AS mom_rate
        FROM car_fuel_stats
        WHERE year_months BETWEEN @period_start_ym AND @latest_ym
          AND car_type='소계' AND usage_type='계' AND region='합계'
        ORDER BY fuel_type, year_months
    """,
    "M2": """
        WITH r AS (
            SELECT year_months, fuel_type, registered_count,
                ROW_NUMBER() OVER (PARTITION BY fuel_type ORDER BY year_months DESC) rn
            FROM car_fuel_stats
            WHERE car_type='소계' AND usage_type='계' AND region='합계'
        ),
        a AS (SELECT fuel_type, AVG(registered_count) avg_r FROM r WHERE rn<=3 GROUP BY fuel_type),
        b AS (SELECT fuel_type, AVG(registered_count) avg_p FROM r WHERE rn BETWEEN 4 AND 6 GROUP BY fuel_type)
        SELECT a.fuel_type,
            ROUND(a.avg_r) recent_3m_avg, ROUND(b.avg_p) prev_3m_avg,
            ROUND(a.avg_r - b.avg_p) abs_diff,
            ROUND((a.avg_r-b.avg_p)/NULLIF(b.avg_p,0)*100,2) change_pct,
            CASE WHEN (a.avg_r-b.avg_p)/NULLIF(b.avg_p,0)>0.005 THEN 'UP'
                 WHEN (a.avg_r-b.avg_p)/NULLIF(b.avg_p,0)<-0.005 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM a JOIN b ON a.fuel_type=b.fuel_type
        ORDER BY change_pct DESC
    """,
    "Y1": """
        SELECT YEAR(STR_TO_DATE(CONCAT(year_months,'01'),'%Y%m%d')) stat_year,
            fuel_type, registered_count,
            ROUND((registered_count
                   - LAG(registered_count) OVER (PARTITION BY fuel_type ORDER BY year_months))
                  / NULLIF(LAG(registered_count) OVER (PARTITION BY fuel_type ORDER BY year_months),0)*100,2) yoy_rate
        FROM car_fuel_stats
        WHERE year_months IN (
            SELECT COALESCE(
                MAX(CASE WHEN RIGHT(year_months,2)='12' THEN year_months END),
                MAX(year_months))
            FROM car_fuel_stats
            WHERE car_type='소계' AND usage_type='계' AND region='합계'
            GROUP BY LEFT(year_months,4)
        )
        AND car_type='소계' AND usage_type='계' AND region='합계'
        ORDER BY fuel_type, stat_year
    """,
    "Y2": """
        WITH p AS (
            SELECT fuel_type,
                SUM(CASE WHEN year_months > DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),INTERVAL 12 MONTH),'%Y%m')
                          AND year_months <= @latest_ym THEN registered_count END) recent_12m,
                SUM(CASE WHEN year_months > DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),INTERVAL 24 MONTH),'%Y%m')
                          AND year_months <= DATE_FORMAT(DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),INTERVAL 12 MONTH),'%Y%m') THEN registered_count END) prev_12m
            FROM car_fuel_stats WHERE car_type='소계' AND usage_type='계' AND region='합계'
            GROUP BY fuel_type
        )
        SELECT fuel_type, recent_12m, prev_12m, recent_12m-prev_12m diff,
            ROUND((recent_12m-prev_12m)/NULLIF(prev_12m,0)*100,2) yoy_rate,
            CASE WHEN recent_12m>prev_12m*1.05 THEN 'UP'
                 WHEN recent_12m<prev_12m*0.95 THEN 'DOWN' ELSE 'FLAT' END trend_direction
        FROM p WHERE prev_12m>0 ORDER BY yoy_rate DESC
    """,
    # 차종·배기량
    "M3": """
        SELECT year_months, car_subtype, registered_count,
            ROUND(registered_count
                  / NULLIF(MAX(CASE WHEN car_subtype='계' THEN registered_count END)
                             OVER (PARTITION BY year_months),0)*100,2) share_pct
        FROM car_type_detail_stats
        WHERE year_months BETWEEN @period_start_ym AND @latest_ym
          AND car_type='승용' AND region='합계'
        ORDER BY year_months, car_subtype
    """,
    "M4": """
        SELECT year_months, displacement, registered_count,
            registered_count - LAG(registered_count)
                OVER (PARTITION BY displacement ORDER BY year_months) mom_diff
        FROM car_displacement_stats
        WHERE year_months BETWEEN @period_start_ym AND @latest_ym AND region='합계'
        ORDER BY displacement, year_months
    """,
    "Y3": """
        SELECT stat_year, car_type, registered_count,
            ROUND((registered_count
                   - LAG(registered_count) OVER (PARTITION BY car_type ORDER BY stat_year))
                  / NULLIF(LAG(registered_count) OVER (PARTITION BY car_type ORDER BY stat_year),0)*100,2) yoy_rate
        FROM car_yearly_stats
        WHERE usage_type='합계'
          AND stat_year < YEAR(CURDATE())
          AND stat_year >= YEAR(CURDATE()) - 10
        ORDER BY car_type, stat_year
    """,
    "Y4": """
        SELECT stat_year, registered_count,
            ROUND((registered_count - LAG(registered_count) OVER (ORDER BY stat_year))
                  / NULLIF(LAG(registered_count) OVER (ORDER BY stat_year),0)*100,2) yoy_rate
        FROM car_yearly_stats
        WHERE car_type='합계' AND usage_type='합계'
          AND stat_year < YEAR(CURDATE())
          AND stat_year >= YEAR(CURDATE()) - 10
        ORDER BY stat_year
    """,
    # 구매층
    "M5": """
        SELECT year_months, gender, age_group, registered_count,
            registered_count - LAG(registered_count)
                OVER (PARTITION BY gender, age_group ORDER BY year_months) mom_diff
        FROM car_gender_age_stats
        WHERE year_months BETWEEN @period_start_ym AND @latest_ym
          AND region='합계' AND gender IN ('남성','여성')
          AND age_group IN ('20대','30대','40대','50대','60대','70대','80대','90대이상')
        ORDER BY year_months, gender, age_group
    """,
    "M6": """
        WITH r AS (
            SELECT year_months, gender, age_group, registered_count,
                ROW_NUMBER() OVER (PARTITION BY gender, age_group ORDER BY year_months DESC) rn
            FROM car_gender_age_stats
            WHERE region='합계' AND gender IN ('남성','여성')
              AND age_group IN ('20대','30대','40대','50대','60대','70대','80대','90대이상')
        )
        SELECT gender, age_group,
            ROUND(AVG(CASE WHEN rn<=3 THEN registered_count END)) recent_3m_avg,
            ROUND(AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END)) prev_3m_avg,
            ROUND(AVG(CASE WHEN rn<=3 THEN registered_count END))
                - ROUND(AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END)) abs_diff,
            ROUND((AVG(CASE WHEN rn<=3 THEN registered_count END)
                   - AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END))
                  / NULLIF(AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END),0)*100,2) change_pct,
            CASE WHEN AVG(CASE WHEN rn<=3 THEN registered_count END)
                    > AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END)*1.005 THEN 'UP'
                 WHEN AVG(CASE WHEN rn<=3 THEN registered_count END)
                    < AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END)*0.995 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM r GROUP BY gender, age_group
        ORDER BY FIELD(age_group,'20대','30대','40대','50대','60대','70대','80대','90대이상'), gender
    """,
    # 지역
    "M7": """
        WITH l AS (SELECT region, cnt_total FROM car_region_stats WHERE year_months=@latest_ym AND car_type='합계'),
             b AS (SELECT region, cnt_total FROM car_region_stats WHERE year_months=@start_ym  AND car_type='합계')
        SELECT l.region, b.cnt_total base_cnt, l.cnt_total latest_cnt,
            l.cnt_total - b.cnt_total diff,
            ROUND((l.cnt_total-b.cnt_total)/NULLIF(b.cnt_total,0)*100,2) growth_pct,
            CASE WHEN (l.cnt_total-b.cnt_total)/NULLIF(b.cnt_total,0)>0.03 THEN 'UP'
                 WHEN (l.cnt_total-b.cnt_total)/NULLIF(b.cnt_total,0)<-0.01 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM l JOIN b ON l.region=b.region WHERE l.region!='합계'
        ORDER BY growth_pct DESC
    """,
    # 수입
    "Y5": """
        SELECT year_months,
            SUM(CASE WHEN reg_type='신조차' THEN registered_count END) sinjo,
            SUM(CASE WHEN reg_type='수입차' THEN registered_count END) import_cnt,
            SUM(CASE WHEN reg_type='부활차' THEN registered_count END) buhwal,
            SUM(CASE WHEN reg_type='계'     THEN registered_count END) total_cnt,
            ROUND(SUM(CASE WHEN reg_type='수입차' THEN registered_count END)
                  / NULLIF(SUM(CASE WHEN reg_type='계' THEN registered_count END),0)*100,2) import_pct
        FROM car_new_registration
        WHERE region='합계' AND car_type='합계'
        GROUP BY year_months ORDER BY year_months
    """,
}


# ============================================================
# 차트 헬퍼
# ============================================================
def trend_badge(direction: str) -> str:
    icons = {"UP": "▲ UP", "DOWN": "▼ DOWN", "FLAT": "━ FLAT"}
    return icons.get(direction, direction)


def color_trend(val):
    c = TREND_COLOR.get(val, "#ffffff")
    return f"background-color:{c}; color:white; border-radius:4px; padding:2px 6px;"


def fmt_num(n) -> str:
    if n is None:
        return "-"
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def fmt_ym(df: pd.DataFrame, col: str = "year_months") -> pd.DataFrame:
    """202401 → '2024.01' 문자열로 변환해 x축 숫자 깨짐 방지"""
    df = df.copy()
    df[col] = df[col].astype(str).str[:4] + "." + df[col].astype(str).str[4:]
    return df


# ============================================================
# 레이아웃
# ============================================================
st.title("🚗 전국 자동차 등록 현황 트렌드 대시보드")

with st.sidebar:
    st.header("⚙️ 분석 기간")
    period = st.select_slider(
        "조회 기간 (개월)",
        options=[6, 12, 24],
        value=12,
        format_func=lambda x: f"{x}개월",
    )
    st.caption("월별 차트는 선택한 기간 기준으로 표시됩니다.")
    st.divider()
    st.caption("데이터: 국토교통부 자동차 등록 현황")

# ── 요약 카드 ──────────────────────────────────────────────
summary = get_summary(period)
df_m2_card = run_query(SQL["M2"], period)

c1, c2, c3, c4 = st.columns(4)
c1.metric("기준 월 (누적 기준)", summary["latest_ym"] or "-")
c2.metric("전체 누적 등록 대수", fmt_num(summary["total_registered"]))

# 가장 상승/급감 중인 연료 동적 표시 (등록수 100 미만 소량 연료 제외)
if not df_m2_card.empty:
    df_m2_sig = df_m2_card[df_m2_card["recent_3m_avg"] >= 100]
    if df_m2_sig.empty:
        df_m2_sig = df_m2_card

    up_rows = df_m2_sig[df_m2_sig["trend_direction"] == "UP"]
    top_up = up_rows.iloc[0] if not up_rows.empty else df_m2_sig.iloc[0]
    c3.metric(
        f"▲ 급증 연료 — {top_up['fuel_type']} (누적 등록)",
        fmt_num(top_up["recent_3m_avg"]),
        delta=f"{top_up['change_pct']:+.1f}% (3개월 평균 변화율)",
    )

    down_rows = df_m2_sig[df_m2_sig["trend_direction"] == "DOWN"]
    top_down = down_rows.iloc[-1] if not down_rows.empty else df_m2_sig.iloc[-1]
    c4.metric(
        f"▼ 급감 연료 — {top_down['fuel_type']} (누적 등록)",
        fmt_num(top_down["recent_3m_avg"]),
        delta=f"{top_down['change_pct']:+.1f}% (3개월 평균 변화율)",
        delta_color="inverse",
    )
else:
    c3.metric("급증 연료", "-")
    c4.metric("급감 연료", "-")
st.divider()

# ── 탭 ────────────────────────────────────────────────────
tab_m, tab_y = st.tabs(["📅 월별 트렌드", "📊 연도별 트렌드"])


def show_table(df: pd.DataFrame, rename: dict = None, trend_col: str = "방향"):
    """트렌드 방향 색상 강조 표 출력"""
    d = df.rename(columns=rename) if rename else df.copy()
    if trend_col in d.columns:
        st.dataframe(
            d.style.map(color_trend, subset=[trend_col]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.dataframe(d, use_container_width=True, hide_index=True)


# ============================================================
# 월별 탭
# ============================================================
with tab_m:

    # M-1 연료별 월별 현황
    st.subheader(f"M-1 · 연료별 월별 등록 현황 (최근 {period}개월)")
    df_m1 = run_query(SQL["M1"], period)
    if not df_m1.empty:
        pivot_m1 = df_m1.pivot_table(
            index="fuel_type", columns="year_months",
            values="registered_count", aggfunc="first",
        )
        pivot_m1 = pivot_m1.sort_values(pivot_m1.columns[-1], ascending=False)
        pivot_m1.columns = [str(c)[:4] + "." + str(c)[4:] for c in pivot_m1.columns]
        pivot_m1.index.name = "연료"
        st.dataframe(pivot_m1.map(lambda x: f"{int(x):,}" if pd.notna(x) else "-"),
                     use_container_width=True)
    st.divider()

    # M-2 연료별 단기 트렌드 방향
    st.subheader("M-2 · 연료별 단기 트렌드 방향 (최근 3개월 vs 이전 3개월)")
    df_m2 = run_query(SQL["M2"], period)
    if not df_m2.empty:
        show_table(
            df_m2[["fuel_type", "recent_3m_avg", "prev_3m_avg",
                   "abs_diff", "change_pct", "trend_direction"]],
            rename={"fuel_type": "연료", "recent_3m_avg": "최근3개월 평균",
                    "prev_3m_avg": "이전3개월 평균", "abs_diff": "절대 증감",
                    "change_pct": "변화율(%)", "trend_direction": "방향"},
        )
    st.divider()

    # M-3 차종별 비중
    st.subheader(f"M-3 · 승용 차종별 비중 추이 (최근 {period}개월)")
    df_m3 = run_query(SQL["M3"], period)
    if not df_m3.empty:
        pivot_m3 = df_m3[~df_m3["car_subtype"].isin(["계"])].pivot_table(
            index="car_subtype", columns="year_months",
            values="share_pct", aggfunc="first",
        )
        latest_col = pivot_m3.columns.max()
        pivot_m3 = pivot_m3.sort_values(latest_col, ascending=False)
        pivot_m3.columns = [str(c)[:4] + "." + str(c)[4:] for c in pivot_m3.columns]
        pivot_m3.index.name = "차종"
        st.dataframe(pivot_m3.round(1), use_container_width=True)
    st.divider()

    # M-4 배기량별 현황
    st.subheader(f"M-4 · 배기량별 등록 현황 추이 (최근 {period}개월)")
    df_m4 = run_query(SQL["M4"], period)
    if not df_m4.empty:
        pivot_m4 = df_m4.pivot_table(
            index="displacement", columns="year_months",
            values="registered_count", aggfunc="first",
        )
        latest_col = pivot_m4.columns.max()
        pivot_m4 = pivot_m4.sort_values(latest_col, ascending=False)
        pivot_m4.columns = [str(c)[:4] + "." + str(c)[4:] for c in pivot_m4.columns]
        pivot_m4.index.name = "배기량"
        st.dataframe(pivot_m4.map(lambda x: f"{int(x):,}" if pd.notna(x) else "-"),
                     use_container_width=True)
    st.divider()

    # M-5 + M-6 구매층 트렌드 (합쳐서 표시)
    st.subheader("M-5 · 성별·연령대 트렌드 방향")
    df_m6 = run_query(SQL["M6"], period)
    if not df_m6.empty:
        col_m, col_f = st.columns(2)
        for col, gender in zip([col_m, col_f], ["남성", "여성"]):
            with col:
                st.caption(f"**{gender}**")
                df_g = df_m6[df_m6["gender"] == gender][
                    ["age_group", "recent_3m_avg", "prev_3m_avg",
                     "abs_diff", "change_pct", "trend_direction"]
                ].copy()
                df_g.columns = ["연령대", "최근3개월", "이전3개월",
                                "절대증감", "변화율%", "방향"]
                st.dataframe(
                    df_g.style.map(color_trend, subset=["방향"]),
                    use_container_width=True, hide_index=True,
                )
    with st.expander("월별 상세 데이터 (M-5)"):
        df_m5 = run_query(SQL["M5"], period)
        if not df_m5.empty:
            st.dataframe(fmt_ym(df_m5), use_container_width=True, hide_index=True)
    st.divider()

    # M-7 지역별 증감 순위
    st.subheader("M-7 · 지역별 등록 증감 순위")
    df_m7 = run_query(SQL["M7"], period)
    if not df_m7.empty:
        show_table(
            df_m7[["region", "base_cnt", "latest_cnt",
                   "diff", "growth_pct", "trend_direction"]],
            rename={"region": "지역", "base_cnt": "기준 등록수",
                    "latest_cnt": "최신 등록수", "diff": "증감",
                    "growth_pct": "성장률(%)", "trend_direction": "방향"},
        )


# ============================================================
# 연도별 탭
# ============================================================
with tab_y:

    # Y-1 연료별 연간 등록 현황
    st.subheader("Y-1 · 연료별 연간 등록 현황 (연도별)")
    df_y1 = run_query(SQL["Y1"], period)
    if not df_y1.empty:
        # 연도별 피벗 테이블로 표시
        pivot = df_y1.pivot_table(
            index="fuel_type", columns="stat_year",
            values="registered_count", aggfunc="first",
        )
        pivot.columns = pivot.columns.astype(str)
        st.dataframe(pivot.map(lambda x: f"{int(x):,}" if pd.notna(x) else "-"),
                     use_container_width=True)
        with st.expander("전년 대비 증감률(%) 상세"):
            pivot_rate = df_y1.pivot_table(
                index="fuel_type", columns="stat_year",
                values="yoy_rate", aggfunc="first",
            )
            pivot_rate.columns = pivot_rate.columns.astype(str)
            st.dataframe(pivot_rate.round(1), use_container_width=True)
    st.divider()

    # Y-2 연료별 장기 성장 순위
    st.subheader("Y-2 · 연료별 장기 성장 순위 (최근 12개월 vs 이전 12개월)")
    df_y2 = run_query(SQL["Y2"], period)
    if not df_y2.empty:
        show_table(
            df_y2[["fuel_type", "recent_12m", "prev_12m",
                   "diff", "yoy_rate", "trend_direction"]],
            rename={"fuel_type": "연료", "recent_12m": "최근12개월",
                    "prev_12m": "이전12개월", "diff": "증감",
                    "yoy_rate": "성장률(%)", "trend_direction": "방향"},
        )
    st.divider()

    # Y-3 차종별 연도별 증감
    st.subheader("Y-3 · 차종별 연도별 등록 현황")
    df_y3 = run_query(SQL["Y3"], period)
    if not df_y3.empty:
        pivot = df_y3.pivot_table(
            index="car_type", columns="stat_year",
            values="registered_count", aggfunc="first",
        )
        pivot.columns = pivot.columns.astype(str)
        st.dataframe(pivot.map(lambda x: f"{int(x):,}" if pd.notna(x) else "-"),
                     use_container_width=True)
        with st.expander("전년 대비 증감률(%) 상세"):
            pivot_rate = df_y3.pivot_table(
                index="car_type", columns="stat_year",
                values="yoy_rate", aggfunc="first",
            )
            pivot_rate.columns = pivot_rate.columns.astype(str)
            st.dataframe(pivot_rate.round(1), use_container_width=True)
    st.divider()

    # Y-4 전체 시장 연도별 증감
    st.subheader("Y-4 · 전체 시장 연도별 규모 및 성장률")
    df_y4 = run_query(SQL["Y4"], period)
    if not df_y4.empty:
        df_y4_disp = df_y4.copy()
        df_y4_disp["stat_year"] = df_y4_disp["stat_year"].astype(str)
        df_y4_disp["registered_count"] = df_y4_disp["registered_count"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "-"
        )
        show_table(
            df_y4_disp[["stat_year", "registered_count", "yoy_rate"]],
            rename={"stat_year": "연도", "registered_count": "전체 등록수",
                    "yoy_rate": "전년 대비(%)"},
        )
    st.divider()

    # Y-5 수입차 비중 추이
    st.subheader("Y-5 · 수입차 비중 월별 추이")
    df_y5 = run_query(SQL["Y5"], period)
    if not df_y5.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("최신 수입차 비중", f"{df_y5['import_pct'].iloc[-1]:.1f}%")
        col2.metric("기간 평균 비중", f"{df_y5['import_pct'].mean():.1f}%")
        col3.metric("최고 비중",
                    f"{df_y5['import_pct'].max():.1f}% ({fmt_ym(df_y5).loc[df_y5['import_pct'].idxmax(), 'year_months']})")
        df_y5_disp = fmt_ym(df_y5)[["year_months", "sinjo", "import_cnt",
                                     "buhwal", "total_cnt", "import_pct"]].copy()
        df_y5_disp.columns = ["년월", "신조차", "수입차", "부활차", "합계", "수입비중(%)"]
        st.dataframe(df_y5_disp, use_container_width=True, hide_index=True)
