import time
import re
import os
import mysql.connector
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ─────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "use_unicode": True,
}

ONSTAR_TAB_TARGETS = [
    {
        "category": "온스타 서비스",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq",
    },
    {
        "category": "휴대폰 앱",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/mobile-phone-app",
    },
    {
        "category": "원격 차량 제어",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/remote-vehicle-control",
    },
    {
        "category": "차량진단",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/vehicle-diagnosis",
    },
    {
        "category": "전기차 관련 기능",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/ev-related-functions",
    },
    {
        "category": "무선 소프트웨어 업데이트(OTA)",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/over-the-air",
    },
    {
        "category": "TMAP AUTO & NUGU AUTO",
        "url": "https://www.cadillac.co.kr/onstar/onstar-faq/tmap-auto-nugu-auto",
    },
]


# ── 2. 텍스트 정제 ───────────────────────────────────────────────────────────────
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


# ── 3. DB 헬퍼 ──────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def insert_faq(cursor, category, question, answer):
    # 동일한 브랜드 내에서 같은 질문이 있는지 체크 (uq_brand_question 대응)
    cursor.execute(
        "SELECT id FROM company_faq WHERE brand = %s AND question = %s LIMIT 1",
        ("캐딜락", question[:500]),
    )
    if cursor.fetchone():
        return False

    # 통합 테이블 구조에 맞게 brand('캐딜락')를 명시하여 INSERT
    cursor.execute(
        "INSERT INTO company_faq (brand, category, question, answer) VALUES (%s, %s, %s, %s)",
        ("캐딜락", category, question, answer),
    )
    return True


# ── 4. 이미지 돔(DOM) 매핑 맞춤형 파서 ──────────────────────────────────────────────
def extract_onstar_faq(html: str, tab_category: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    seen: set[str] = set()

    for expander in soup.select("gb-expander"):
        q_text = expander.get("open-headline", "")
        if not q_text:
            h2_el = expander.select_one("h2.gb-expander-headline")
            if h2_el:
                q_text = h2_el.get_text()

        answer_box = expander.select_one("div.gb-expander-content-body")
        a_text = ""
        if answer_box:
            p_tags = answer_box.select("p")
            if p_tags:
                a_text = " ".join(
                    [p.get_text() for p in p_tags if p.get_text().strip()]
                )
            else:
                a_text = answer_box.get_text()

        q = clean(q_text)
        a = clean(a_text)

        if not q or len(q) < 5 or q in seen:
            continue

        seen.add(q)
        items.append({"category": tab_category, "question": q, "answer": a})

    return items


# ── 5. 브라우저 생성 ─────────────────────────────────────────────────────────────
def make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = webdriver.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=ko-KR")
    opts.add_argument("--headless=new")  # 백그라운드 실행 추가

    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        },
    )

    return driver


# ── 6. 메인 크롤러 로직 ────────────────────────────────────────────────────────────
def crawl() -> int:
    db = get_db()
    cursor = db.cursor()
    # 테이블 생성(ensure_schema) 로직 삭제 -> 사전에 테이블이 생성되어 있어야 합니다.

    total_new = 0
    driver = make_driver()

    try:
        print(f"\n{'='*60}")
        print(f"[크롤링 시작] 캐딜락 온스타 데이터 통합 테이블 수집")
        print(f" 총 타겟 URL 수: {len(ONSTAR_TAB_TARGETS)}개")

        for index, target in enumerate(ONSTAR_TAB_TARGETS):
            category = target["category"]
            url = target["url"]

            print(
                f"\n [{index+1}/{len(ONSTAR_TAB_TARGETS)}] {category} 페이지 렌더링 중..."
            )

            try:
                driver.get(url)
                time.sleep(4)
            except Exception as e:
                print(f"   URL 접속 실패: {e}")
                continue

            html = driver.page_source

            if "Host not in allowlist" in html or len(html) < 500:
                print("   봇 차단 감지되었습니다.")
                continue

            tab_items = extract_onstar_faq(html, category)
            print(f"   -> 수집된 질문: {len(tab_items)}건")

            page_new = 0
            for it in tab_items:
                if insert_faq(cursor, it["category"], it["question"], it["answer"]):
                    page_new += 1
                    total_new += 1

            db.commit()
            print(f"   -> 통합 테이블(company_faq) 신규 저장: {page_new}건")

    finally:
        driver.quit()
        cursor.close()
        db.close()

    return total_new


# ── 7. 결과 출력 ─────────────────────────────────────────────────────────────────
def show_results():
    db = get_db()
    cur = db.cursor()

    # 캐딜락 데이터만 선별하여 통계 산출
    cur.execute("SELECT COUNT(*) FROM company_faq WHERE brand = '캐딜락'")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(NULLIF(category,''), '(없음)') AS cat, COUNT(*) AS cnt
        FROM company_faq 
        WHERE brand = '캐딜락'
        GROUP BY cat 
        ORDER BY cnt DESC
    """)
    by_cat = cur.fetchall()

    cur.close()
    db.close()

    print(f"\n{'='*60}")
    print(f"캐딜락 수집 결과 보고서 | 통합 디비 내 캐딜락 데이터: {total}건\n")
    print("카테고리별 저장 현황:")
    for cat, cnt in by_cat:
        print(f"  · {cat}: {cnt}건")
    print(f"{'='*60}")


# ── 진입점 ───────────────────────────────────────────────────────────────────
def run():
    try:
        new_count = crawl()
        print(f"\n완료! 새롭게 수집된 캐딜락 FAQ: {new_count}건")
        show_results()
    except Exception as e:
        print(f"\n크롤러 구동 실패 원인: {e}")


if __name__ == "__main__":
    run()
