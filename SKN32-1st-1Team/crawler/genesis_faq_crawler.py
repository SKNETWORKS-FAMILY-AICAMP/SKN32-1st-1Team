import re
import json
import os
import mysql.connector
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":       os.getenv("DB_HOST",     "localhost"),
    "port":       int(os.getenv("DB_PORT", "3306")),
    "user":       os.getenv("DB_USER",     "homework"),
    "password":   os.getenv("DB_PASSWORD", "playdatahomework80"),
    "database":   os.getenv("DB_NAME",     "car_project_db"),
    "charset":    "utf8mb4",
    "use_unicode": True,
}

TARGET_URL = "https://www.genesis.com/kr/ko/support/faq.html"

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
EXTRA_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://www.genesis.com/kr/ko/",
}


# ── 텍스트 정제 ───────────────────────────────────────────────────────────────
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


# ── DB 헬퍼 ──────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def insert_faq(cursor, category, question, answer):
    """brand와 question 기준 중복 체크 후 INSERT (uq_brand_question 대응)"""
    cursor.execute(
        "SELECT id FROM company_faq WHERE brand = %s AND question = %s LIMIT 1",
        ("제네시스", question[:500]),
    )
    if cursor.fetchone():
        return False

    # 통합 테이블 구조에 맞게 brand('제네시스')를 포함하여 데이터 저장
    cursor.execute(
        """INSERT INTO company_faq (brand, category, question, answer)
           VALUES (%s, %s, %s, %s)""",
        ("제네시스", category, question, answer),
    )
    return True


# ── 페이지 파서 ───────────────────────────────────────────────────────────────
def extract_faq_items(page) -> list[dict]:
    soup = BeautifulSoup(page.content(), "html.parser")
    items: list[dict] = []
    seen: set[str] = set()

    for item in soup.select("div.cp-faq__accordion-item"):
        label_el = item.select_one("strong.accordion-label")
        title_el = item.select_one("p.accordion-title")
        panel_el = item.select_one("div.accordion-panel")

        if not title_el:
            continue

        category = clean(label_el.get_text()) if label_el else ""
        # [차량 구매] 형태에서 대괄호 제거
        category = re.sub(r"^\[|\]$", "", category).strip()

        question = clean(title_el.get_text())
        answer = clean(panel_el.get_text()) if panel_el else ""

        if not question or question in seen:
            continue
        seen.add(question)

        items.append(
            {
                "category": category,
                "question": question,
                "answer": answer,
            }
        )

    return items


# ── 메인 크롤러 ──────────────────────────────────────────────────────────────
def crawl() -> int:
    db = get_db()
    cursor = db.cursor()
    # 테이블 생성(ensure_schema) 로직 삭제 -> 사전에 테이블이 존재해야 합니다.

    print(f"\n{'='*60}")
    print(f"[크롤링] 제네시스 전체 FAQ -> 통합 테이블 연동")
    print(f" URL: {TARGET_URL}")

    total_new = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=BROWSER_ARGS)
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
            extra_http_headers=EXTRA_HEADERS,
        )
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
        )

        page = context.new_page()
        loaded = False
        for strategy in ("networkidle", "domcontentloaded", "load"):
            try:
                resp = page.goto(TARGET_URL, wait_until=strategy, timeout=30_000)
                status = resp.status if resp else 0
                print(f"  HTTP {status}  (strategy={strategy})")
                if status == 403:
                    print("  HTTP 403 — 봇 차단. 로컬/서버 환경에서 실행하세요.")
                    break
                page.wait_for_timeout(3000)
                loaded = True
                break
            except PWTimeout:
                print(f"  {strategy} 타임아웃, 다음 전략으로…")
            except Exception as e:
                print(f"  ❌ {e}")
                break

        if loaded:
            all_items = extract_faq_items(page)

            # 중복 제거
            seen_q: set[str] = set()
            deduped = []
            for it in all_items:
                if it["question"] not in seen_q:
                    seen_q.add(it["question"])
                    deduped.append(it)

            print(f"  추출 성공: {len(deduped)}건")

            for it in deduped:
                if insert_faq(cursor, it["category"], it["question"], it["answer"]):
                    total_new += 1

            db.commit()
            print(f"  통합 테이블(company_faq) 신규 저장: {total_new}건")

        page.close()
        browser.close()

    cursor.close()
    db.close()
    return total_new


# ── 결과 출력 ─────────────────────────────────────────────────────────────────
def show_results():
    db = get_db()
    cur = db.cursor()

    # 제네시스 데이터만 선별하여 통계 산출
    cur.execute("SELECT COUNT(*) FROM company_faq WHERE brand = '제네시스'")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(NULLIF(category,''), '(없음)') AS cat, COUNT(*) AS cnt
        FROM company_faq 
        WHERE brand = '제네시스'
        GROUP BY cat 
        ORDER BY cnt DESC
    """)
    by_cat = cur.fetchall()

    cur.close()
    db.close()

    print(f"\n{'='*60}")
    print(f"제네시스 수집 결과 보고서 | 통합 디비 내 제네시스 데이터: {total}건\n")
    print("카테고리별 저장 현황:")
    for cat, cnt in by_cat:
        print(f"  · {cat}: {cnt}건")
    print(f"{'='*60}")


# ── 진입점 ───────────────────────────────────────────────────────────────────
def run():
    print("제네시스 전체 FAQ 크롤러")
    print("  · Playwright(Chromium) 동적 렌더링")
    print("  · 통합 테이블(company_faq) 맞춤형 주입")
    try:
        new_count = crawl()
        print(f"\n완료! 새롭게 수집된 제네시스 FAQ: {new_count}건")
        show_results()
    except Exception as e:
        print(f"\n크롤러 구동 실패 원인: {e}")


if __name__ == "__main__":
    run()
