"""
전국 자동차 등록 현황 트렌드 대시보드 — 모듈 버전
원본: app.py  /  show() 로 래핑하여 Appmain.py 에서 호출
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from modules.connect_db import run_query, get_summary

CHART_COLORWAY = ["#2477bd", "#5aa9df", "#174f84", "#8fc7ec", "#315a7c", "#6f9dc5"]
px.defaults.color_discrete_sequence = CHART_COLORWAY
TREND_COLOR = {"UP": "#16a34a", "DOWN": "#dc2626", "FLAT": "#52677a"}

# ============================================================
# SQL 정의
# ============================================================
SQL = {
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
        a AS (SELECT fuel_type, AVG(registered_count) avg_r FROM r WHERE rn<=6 GROUP BY fuel_type),
        b AS (SELECT fuel_type, AVG(registered_count) avg_p FROM r WHERE rn BETWEEN 7 AND 12 GROUP BY fuel_type)
        SELECT a.fuel_type,
            ROUND(a.avg_r) recent_6m_avg, ROUND(b.avg_p) prev_6m_avg,
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
    "M3": """
        WITH r AS (
            SELECT year_months, car_subtype, registered_count,
                ROW_NUMBER() OVER (PARTITION BY car_subtype ORDER BY year_months DESC) rn
            FROM car_type_detail_stats
            WHERE car_type='승용' AND region='합계' AND car_subtype != '계'
        ),
        a AS (SELECT car_subtype, ROUND(AVG(registered_count)) avg_r FROM r WHERE rn<=6 GROUP BY car_subtype),
        b AS (SELECT car_subtype, ROUND(AVG(registered_count)) avg_p FROM r WHERE rn BETWEEN 7 AND 12 GROUP BY car_subtype)
        SELECT a.car_subtype,
            a.avg_r recent_6m_avg, b.avg_p prev_6m_avg,
            a.avg_r - b.avg_p abs_diff,
            ROUND((a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) * 100, 2) change_pct,
            CASE WHEN (a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) > 0.005 THEN 'UP'
                 WHEN (a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) < -0.005 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM a JOIN b ON a.car_subtype = b.car_subtype
        ORDER BY change_pct DESC
    """,
    "M4": """
        WITH r AS (
            SELECT year_months, displacement, registered_count,
                ROW_NUMBER() OVER (PARTITION BY displacement ORDER BY year_months DESC) rn
            FROM car_displacement_stats
            WHERE region='합계'
        ),
        a AS (SELECT displacement, ROUND(AVG(registered_count)) avg_r FROM r WHERE rn<=6 GROUP BY displacement),
        b AS (SELECT displacement, ROUND(AVG(registered_count)) avg_p FROM r WHERE rn BETWEEN 7 AND 12 GROUP BY displacement)
        SELECT a.displacement,
            a.avg_r recent_6m_avg, b.avg_p prev_6m_avg,
            a.avg_r - b.avg_p abs_diff,
            ROUND((a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) * 100, 2) change_pct,
            CASE WHEN (a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) > 0.005 THEN 'UP'
                 WHEN (a.avg_r - b.avg_p) / NULLIF(b.avg_p, 0) < -0.005 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM a JOIN b ON a.displacement = b.displacement
        ORDER BY change_pct DESC
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
            ROUND(AVG(CASE WHEN rn<=6 THEN registered_count END)) recent_6m_avg,
            ROUND(AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END)) prev_6m_avg,
            ROUND(AVG(CASE WHEN rn<=6 THEN registered_count END))
                - ROUND(AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END)) abs_diff,
            ROUND((AVG(CASE WHEN rn<=6 THEN registered_count END)
                   - AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END))
                  / NULLIF(AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END),0)*100,2) change_pct,
            CASE WHEN AVG(CASE WHEN rn<=6 THEN registered_count END)
                    > AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END)*1.005 THEN 'UP'
                 WHEN AVG(CASE WHEN rn<=6 THEN registered_count END)
                    < AVG(CASE WHEN rn BETWEEN 7 AND 12 THEN registered_count END)*0.995 THEN 'DOWN'
                 ELSE 'FLAT' END trend_direction
        FROM r GROUP BY gender, age_group
        ORDER BY FIELD(age_group,'20대','30대','40대','50대','60대','70대','80대','90대이상'), gender
    """,
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
# 차트 및 유틸리티 헬퍼 함수
# ============================================================
def trend_badge(direction: str) -> str:
    icons = {"UP": "▲ UP", "DOWN": "▼ DOWN", "FLAT": "━ FLAT"}
    return icons.get(direction, direction)


def color_trend(val) -> str:
    c = TREND_COLOR.get(val, "#ffffff")
    return f"background-color:{c}; color:white; border-radius:4px; padding:2px 6px;"


def fmt_num(n) -> str:
    if n is None or pd.isna(n):
        return "-"
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def fmt_ym(df: pd.DataFrame, col: str = "year_months") -> pd.DataFrame:
    df_copy = df.copy()
    df_copy[col] = df_copy[col].astype(str).str[:4] + "." + df_copy[col].astype(str).str[4:]
    return df_copy


def fmt_trend(val, threshold: float = 0.5) -> str:
    if pd.isna(val):
        return "-"
    try:
        v = float(val)
    except (ValueError, TypeError):
        return str(val)
        
    if v > threshold:
        return f"▲ UP(+{v:.1f}%)"
    elif v < -threshold:
        return f"▼ DOWN({v:.1f}%)"
    else:
        sign = "+" if v >= 0 else ""
        return f"━ FLAT({sign}{v:.1f}%)"


def color_trend_str(val) -> str:
    if isinstance(val, str):
        if val.startswith("▲"):
            return "color: #16a34a; font-weight: 600"
        elif val.startswith("▼"):
            return "color: #dc2626; font-weight: 600"
        elif val.startswith("━"):
            return "color: #52677a; font-weight: 600"
    return ""


def _ym_sub(ym_str: str, months: int) -> str:
    if not ym_str or len(ym_str) != 6:
        return ym_str
    y, m = int(ym_str[:4]), int(ym_str[4:])
    m -= months
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}.{m:02d}"


def _ym_fmt(ym_str: str) -> str:
    s = str(ym_str)
    return s[:4] + "." + s[4:] if len(s) == 6 else s


# ============================================================
# 메인 렌더링 함수
# ============================================================
def show():
    st.title("🚗 전국 자동차 등록 현황 트렌드 대시보드")
    st.caption("데이터: 국토교통부 자동차 등록 현황")

    summary = get_summary()
    if not summary:
        st.warning("데이터베이스에서 요약 정보를 불러오지 못했습니다.")
        return

    df_m2_card = run_query(SQL["M2"])

    if not df_m2_card.empty:
        df_sig_top3 = df_m2_card[df_m2_card["recent_6m_avg"] >= 100]
        if df_sig_top3.empty:
            df_sig_top3 = df_m2_card
        top3_fuels = df_sig_top3.head(3)["fuel_type"].tolist()
        st.session_state.trend_keywords = top3_fuels

    _lym = str(summary.get("latest_ym", ""))
    _sym = str(summary.get("start_ym", ""))
    
    if len(_lym) == 6:
        _recent_end = _ym_fmt(_lym)
        _recent_start = _ym_sub(_lym, 5)
        _prev_end = _ym_sub(_lym, 6)
        _prev_start = _ym_sub(_lym, 11)
        _cap_6m = f"최근 6개월: {_recent_start} ~ {_recent_end}  |  이전 6개월: {_prev_start} ~ {_prev_end}"
    else:
        _cap_6m = "기간 정보 없음"
        
    _s_label = _ym_fmt(_sym)
    _l_label = _ym_fmt(_lym)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("기준 월 (누적 기준)", _l_label if _l_label else "-")
    c2.metric("전체 누적 등록 대수", fmt_num(summary.get("total_registered")))

    if not df_m2_card.empty:
        df_m2_sig = df_m2_card[df_m2_card["recent_6m_avg"] >= 100]
        if df_m2_sig.empty:
            df_m2_sig = df_m2_card

        up_rows = df_m2_sig[df_m2_sig["trend_direction"] == "UP"]
        top_up = up_rows.iloc[0] if not up_rows.empty else df_m2_sig.iloc[0]
        c3.metric(
            f"▲ 급증 연료 — {top_up['fuel_type']} (누적 등록)",
            fmt_num(top_up["recent_6m_avg"]),
            delta=f"{top_up['change_pct']:+.1f}% (6개월 평균 변화율)",
        )

        down_rows = df_m2_sig[df_m2_sig["trend_direction"] == "DOWN"]
        top_down = down_rows.iloc[-1] if not down_rows.empty else df_m2_sig.iloc[-1]
        c4.metric(
            f"▼ 급감 연료 — {top_down['fuel_type']} (누적 등록)",
            fmt_num(top_down["recent_6m_avg"]),
            delta=f"{top_down['change_pct']:+.1f}% (6개월 평균 변화율)",
        )
    else:
        c3.metric("급증 연료", "-")
        c4.metric("급감 연료", "-")
        
    st.divider()

    tab_m, tab_y = st.tabs(["📅 월별 트렌드", "📊 연도별 트렌드"])

    # ── 1. 월별 탭 ────────────────────────────────────────────
    with tab_m:
        st.subheader("연료별 단기 트렌드")
        st.caption(f"연료 유형별 누적 등록 대수 평균 비교  |  {_cap_6m}")
        df_m2 = run_query(SQL["M2"])
        if not df_m2.empty:
            df_m2_disp = df_m2.copy()
            df_m2_disp["트렌드"] = df_m2_disp["change_pct"].apply(fmt_trend)
            
            df_m2_styled = (
                df_m2_disp[["fuel_type", "recent_6m_avg", "prev_6m_avg", "abs_diff", "트렌드"]]
                .rename(columns={
                    "fuel_type": "연료", 
                    "recent_6m_avg": "최근6개월 평균",
                    "prev_6m_avg": "이전6개월 평균", 
                    "abs_diff": "절대 증감"
                })
                .style.map(color_trend_str, subset=["트렌드"])
            )
            
            sel = st.dataframe(
                df_m2_styled,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-cell",
                key="df_m2_sel",
            )
            
            top3_kws = st.session_state.get("trend_keywords", [])
            if top3_kws:
                kw_tags = "  |  ".join(f"**{k}**" for k in top3_kws)
                st.caption(f"📌 FAQ 트렌드 키워드 자동 전달 중 → {kw_tags}  (첫 번째 키워드 기본 선택)")
            st.caption("💡 연료 셀을 클릭하면 FAQ 검색창에 자동 입력되어 이동합니다.")

            cells = sel.selection.get("cells", [])
            if cells:
                row_idx, col_name = cells[0][0], cells[0][1]
                if col_name == "연료":
                    selected_fuel = df_m2_disp.iloc[row_idx]["fuel_type"]
                    st.session_state.faq_search_input = selected_fuel
                    st.session_state["_faq_last_brands"] = None 
                    st.session_state.page = "faq"
                    st.rerun()
        st.divider()

        st.subheader("승용 차종별 트렌드")
        st.caption(f"승용차 세부 차종별 월평균 등록 대수 비교  |  {_cap_6m}")
        df_m3 = run_query(SQL["M3"])
        if not df_m3.empty:
            df_m3_disp = df_m3.copy()
            df_m3_disp["트렌드"] = df_m3_disp["change_pct"].apply(fmt_trend)
            st.dataframe(
                df_m3_disp[["car_subtype", "recent_6m_avg", "prev_6m_avg", "abs_diff", "트렌드"]]
                .rename(columns={
                    "car_subtype": "차종",
                    "recent_6m_avg": "최근6개월 평균",
                    "prev_6m_avg": "이전6개월 평균",
                    "abs_diff": "절대 증감",
                })
                .style.map(color_trend_str, subset=["트렌드"]),
                use_container_width=True,
                hide_index=True,
            )
        st.divider()

        st.subheader("배기량별 트렌드")
        st.caption(f"배기량 구간별 월평균 등록 대수 비교  |  {_cap_6m}")
        df_m4 = run_query(SQL["M4"])
        if not df_m4.empty:
            df_m4_disp = df_m4.copy()
            df_m4_disp["트렌드"] = df_m4_disp["change_pct"].apply(fmt_trend)
            st.dataframe(
                df_m4_disp[["displacement", "recent_6m_avg", "prev_6m_avg", "abs_diff", "트렌드"]]
                .rename(columns={
                    "displacement": "배기량",
                    "recent_6m_avg": "최근6개월 평균",
                    "prev_6m_avg": "이전6개월 평균",
                    "abs_diff": "절대 증감",
                })
                .style.map(color_trend_str, subset=["트렌드"]),
                use_container_width=True,
                hide_index=True,
            )
        st.divider()

        st.subheader("성별·연령대 트렌드")
        st.caption(f"성별·연령대별 신규 등록 대수 월평균 비교  |  {_cap_6m}")
        df_m6 = run_query(SQL["M6"])
        if not df_m6.empty:
            col_m, col_f = st.columns(2)
            for col, gender in zip([col_m, col_f], ["남성", "여성"]):
                with col:
                    st.caption(f"**{gender}**")
                    df_g = df_m6[df_m6["gender"] == gender].copy()
                    df_g["트렌드"] = df_g["change_pct"].apply(fmt_trend)
                    
                    df_g_styled = (
                        df_g[["age_group", "recent_6m_avg", "prev_6m_avg", "abs_diff", "트렌드"]]
                        .rename(columns={
                            "age_group": "연령대", 
                            "recent_6m_avg": "최근6개월", 
                            "prev_6m_avg": "이전6개월", 
                            "abs_diff": "절대증감"
                        })
                        .style.map(color_trend_str, subset=["트렌드"])
                    )
                    st.dataframe(df_g_styled, use_container_width=True, hide_index=True)
        st.divider()

        st.subheader("수입차 비중 월별 추이")
        st.caption(f"월별 신규 등록 중 수입차 비중 추이  |  {_s_label} ~ {_l_label}")
        df_y5 = run_query(SQL["Y5"])
        if not df_y5.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("최신 수입차 비중", f"{df_y5['import_pct'].iloc[-1]:.1f}%")
            col2.metric("기간 평균 비중", f"{df_y5['import_pct'].mean():.1f}%")
            
            df_y5_fmt = fmt_ym(df_y5)
            max_idx = df_y5['import_pct'].idxmax()
            col3.metric(
                "최고 비중",
                f"{df_y5['import_pct'].max():.1f}% ({df_y5_fmt.loc[max_idx, 'year_months']})",
            )

            # 🌟 [X축 오류 수정 핵심 포인트] 
            # Plotly가 숫자로 오인하지 않도록 'year_months' 컬럼을 복사하여 'YYYY-MM' 문자열 포맷으로 강제 변환합니다.
            df_y5_plot = df_y5.copy()
            df_y5_plot["year_months"] = df_y5_plot["year_months"].astype(str).apply(
                lambda x: f"{x[:4]}-{x[4:6]}" if len(x) == 6 else x
            )

            # 차트 렌더링 시 가공된 df_y5_plot 데이터프레임을 사용합니다.
            fig_y5 = px.line(
                df_y5_plot,
                x="year_months",
                y="import_pct",
                labels={"year_months": "년월", "import_pct": "수입비중(%)"},
                markers=True,
            )
            fig_y5.add_hline(
                y=df_y5["import_pct"].mean(),
                line_dash="dash",
                line_color="gray",
                annotation_text="평균",
                annotation_position="bottom right",
            )
            
            # 🌟 xaxis_type="category" 설정을 명시적으로 추가하여 비어 있는 가상의 정수 공간이 축에 생성되는 것을 차단합니다.
            fig_y5.update_layout(
                xaxis_type="category",
                margin=dict(t=20, b=20), 
                xaxis=dict(tickangle=-45)
            )
            st.plotly_chart(fig_y5, use_container_width=True)

            df_y5_tbl = df_y5_fmt[["year_months", "import_cnt", "total_cnt", "import_pct"]].copy()
            df_y5_tbl["전월대비"] = (
                df_y5["import_pct"]
                .diff()
                .apply(lambda x: fmt_trend(x, threshold=0.1) if pd.notna(x) else "-")
            )
            df_y5_tbl.columns = ["년월", "수입차", "신규등록 합계", "수입비중(%)", "전월대비"]
            
            st.dataframe(
                df_y5_tbl.style.map(color_trend_str, subset=["전월대비"]),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("신규등록 구성 상세 (신조차·수입차·부활차)"):
                df_y5_detail = df_y5_fmt[["year_months", "sinjo", "import_cnt", "buhwal", "total_cnt", "import_pct"]].copy()
                df_y5_detail.columns = ["년월", "신조차", "수입차", "부활차", "합계", "수입비중(%)"]
                st.dataframe(df_y5_detail, use_container_width=True, hide_index=True)

    # ── 2. 연도별 탭 ──────────────────────────────────────────
    with tab_y:
        st.subheader("전체 시장 연도별 규모 및 성장률")
        st.caption("연도별 전체 자동차 누적 등록 대수 및 전년 대비 증감률  |  최근 10개년 기준")
        df_y4 = run_query(SQL["Y4"])
        if not df_y4.empty:
            df_y4_disp = df_y4.copy()
            df_y4_disp["연도"] = df_y4_disp["stat_year"].astype(str)
            df_y4_disp["전체 등록수"] = df_y4_disp["registered_count"].apply(fmt_num)
            df_y4_disp["전년 대비"] = df_y4_disp["yoy_rate"].apply(fmt_trend)
            
            st.dataframe(
                df_y4_disp[["연도", "전체 등록수", "전년 대비"]]
                .style.map(color_trend_str, subset=["전년 대비"]),
                use_container_width=True,
                hide_index=True,
            )
        st.divider()

        _y2_recent_start = _ym_sub(_lym, 11)
        _y2_prev_end = _ym_sub(_lym, 12)
        _y2_prev_start = _ym_sub(_lym, 23)
        st.subheader("연료별 장기 성장 순위")
        st.caption(
            f"연료 유형별 연간 등록 합계 비교  |  "
            f"최근 12개월: {_y2_recent_start} ~ {_l_label}  |  "
            f"이전 12개월: {_y2_prev_start} ~ {_y2_prev_end}"
        )
        df_y2 = run_query(SQL["Y2"])
        if not df_y2.empty:
            df_y2_disp = df_y2.copy()
            df_y2_disp["트렌드"] = df_y2_disp["yoy_rate"].apply(fmt_trend)
            st.dataframe(
                df_y2_disp[["fuel_type", "recent_12m", "prev_12m", "diff", "트렌드"]]
                .rename(columns={
                    "fuel_type": "연료",
                    "recent_12m": "최근12개월 합계",
                    "prev_12m": "이전12개월 합계",
                    "diff": "증감",
                })
                .style.map(color_trend_str, subset=["트렌드"]),
                use_container_width=True,
                hide_index=True,
            )
        st.divider()

        st.subheader("차종별 연도별 등록 현황")
        st.caption("차종(승용·승합·화물·특수)별 연도말 기준 누적 등록 대수 및 전년 대비 증감률  |  최근 10개년 기준")
        df_y3 = run_query(SQL["Y3"])
        if not df_y3.empty:
            pivot_cnt = df_y3.pivot_table(
                index="car_type", columns="stat_year", values="registered_count", aggfunc="first"
            )
            pivot_cnt.columns = pivot_cnt.columns.astype(str)
            pivot_cnt.index.name = "차종"
            st.dataframe(
                pivot_cnt.map(lambda x: f"{int(x):,}" if pd.notna(x) else "-"),
                use_container_width=True,
            )
            
            st.caption("전년 대비 증감률")
            pivot_rate = df_y3.pivot_table(
                index="car_type", columns="stat_year", values="yoy_rate", aggfunc="first"
            )
            pivot_rate.columns = pivot_rate.columns.astype(str)
            pivot_rate.index.name = "차종"
            st.dataframe(
                pivot_rate.map(fmt_trend).style.map(color_trend_str),
                use_container_width=True,
            )
        st.divider()

        st.subheader("지역별 등록 증감 순위")
        st.caption(f"시·도별 누적 등록 대수 전체 기간 비교  |  {_s_label} (데이터 시작월) → {_l_label} (최근월)")
        df_m7 = run_query(SQL["M7"])
        if not df_m7.empty:
            df_m7_disp = df_m7.copy()
            df_m7_disp["트렌드"] = df_m7_disp["growth_pct"].apply(fmt_trend)
            st.dataframe(
                df_m7_disp[["region", "base_cnt", "latest_cnt", "diff", "트렌드"]]
                .rename(columns={
                    "region": "지역",
                    "base_cnt": f"등록수 ({_s_label})",
                    "latest_cnt": f"등록수 ({_l_label})",
                    "diff": "증감",
                })
                .style.map(color_trend_str, subset=["트렌드"]),
                use_container_width=True,
                hide_index=True,
            )