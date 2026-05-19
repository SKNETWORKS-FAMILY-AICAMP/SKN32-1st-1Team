"""
modules/connect_db.py
DB 연결 설정 및 공통 쿼리 함수 모음.
trend_dashboard, stats_dashboard, faq_search 에서 공통으로 사용.
"""

import os
import pymysql
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── DB 접속 정보 ───────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "db": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
}


def get_connection() -> pymysql.connections.Connection:
    """pymysql 커넥션 반환."""
    return pymysql.connect(**DB_CONFIG)


# ── trend_dashboard 용 ────────────────────────────────────────
def _init_session(cur):
    """세션 변수(@latest_ym, @start_ym) 및 UTF-8/SQL 모드 초기화."""
    cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute("SET SESSION sql_mode = CONCAT(@@sql_mode, ',NO_UNSIGNED_SUBTRACTION')")
    cur.execute("SET @latest_ym = (SELECT MAX(year_months) FROM load_history)")
    cur.execute("SET @start_ym  = (SELECT MIN(year_months) FROM load_history)")


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    """세션 변수(@latest_ym)를 활용하는 SQL 실행 후 DataFrame 반환."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _init_session(cur)
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_summary() -> dict:
    """trend_dashboard 상단 요약 카드용 집계값 반환."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _init_session(cur)
            cur.execute("""
                SELECT
                    (SELECT MAX(year_months) FROM load_history)            AS latest_ym,
                    (SELECT MIN(year_months) FROM load_history)            AS start_ym,
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
            keys = [
                "latest_ym",
                "start_ym",
                "total_months",
                "total_registered",
                "ev_total",
                "hybrid_total",
                "suv_total",
            ]
            return dict(zip(keys, row))
    finally:
        conn.close()


# ── stats_dashboard 용 ────────────────────────────────────────
@st.cache_data(ttl=600)
def load_data(query: str) -> pd.DataFrame:
    """단순 SELECT 쿼리 실행 후 year_months 포맷(202401→'2024-01') 자동 추가."""
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn)
        conn.close()
        if "year_months" in df.columns:
            df["year_months_fmt"] = (
                df["year_months"]
                .astype(str)
                .apply(lambda x: f"{x[:4]}-{x[4:6]}" if len(x) == 6 else x)
            )
            df = df.sort_values("year_months_fmt")
        return df
    except Exception as e:
        st.error(f"데이터베이스 연결 또는 쿼리 오류: {e}")
        return pd.DataFrame()


# ── faq_search 용 ─────────────────────────────────────────────
def get_brands() -> list[str]:
    """company_faq 테이블에서 브랜드 목록 조회."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT brand FROM company_faq ORDER BY brand")
        brands = [r[0] for r in cur.fetchall()]
        conn.close()
        return brands
    except Exception:
        return []


def fetch_faq(
    keywords: tuple,
    search_text: str,
    brands: tuple,
    keyword_groups: tuple[tuple[str, ...], ...] | None = None,
) -> tuple[str, list]:
    """
    FAQ 검색.
    keyword_groups: 각 내부 tuple이 OR 조건, 외부 tuple 간은 AND 조건.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        conditions, params = [], []

        if search_text:
            conditions.append("(question LIKE %s OR answer LIKE %s)")
            params += [f"%{search_text}%", f"%{search_text}%"]
        elif keyword_groups:
            for group in keyword_groups:
                or_parts = []
                for term in group:
                    or_parts.append("(question LIKE %s OR answer LIKE %s)")
                    params += [f"%{term}%", f"%{term}%"]
                conditions.append("(" + " OR ".join(or_parts) + ")")
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
