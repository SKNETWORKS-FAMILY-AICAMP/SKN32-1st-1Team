import time
import os
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv


# 1. 모델 정의 (통합 DB 컬럼 순서에 맞춤 조정)
@dataclass
class FaqItem:
    brand: str = "폭스바겐"
    category: str = "일반 정비/서비스"
    question: str = ""
    answer: str = ""


# 2. DB 연결 설정
load_dotenv()


def get_engine():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_NAME")

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url)


# [수정됨] 기존 테이블 생성 로직(init_table) 제거 (이미 테이블이 생성되어 있어야 함)


def save_faq_to_db(faq_items):
    if not faq_items:
        print("저장할 데이터가 없습니다.")
        return

    engine = get_engine()
    with engine.connect() as conn:
        # [수정됨] 매번 전체를 지우는 DELETE 방식 대신, 통합 테이블 규격에 맞추어 INSERT IGNORE로 안전하게 주입
        sql = text("""
            INSERT IGNORE INTO company_faq (brand, category, question, answer)
            VALUES (:brand, :category, :question, :answer)
        """)

        inserted_count = 0
        for item in faq_items:
            result = conn.execute(
                sql,
                {
                    "brand": item.brand,
                    "category": item.category,
                    "question": item.question,
                    "answer": item.answer,
                },
            )
            # 삽입 성공 여부 카운트 (INSERT IGNORE에서 무시되면 rowcount가 0이 됩니다)
            if result.rowcount > 0:
                inserted_count += 1

        conn.commit()

    skipped_count = len(faq_items) - inserted_count
    print(
        f"통합 테이블(company_faq) 반영 완료: {inserted_count}건 삽입 / {skipped_count}건 중복 스킵"
    )


# 3. 크롤러 클래스
class VWFaqCrawler:
    def __init__(self):
        self.url = "https://www.volkswagen.co.kr/ko/faq.html"

    def crawl(self):
        faq_list = []
        with sync_playwright() as p:
            # 백그라운드 자동화를 위해 headless=True로 변경 (눈으로 확인하려면 False로 수정 가능)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 1024})
            page = context.new_page()

            print(f"접속 중: {self.url}")
            page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)

            print("'Show More' 버튼을 화면에 띄우기 위해 스크롤을 내립니다...")
            for i in range(8):
                page.evaluate("window.scrollBy(0, 800);")
                time.sleep(1)

            try:
                btn_selector = "button:has-text('Show More')"
                page.wait_for_selector(btn_selector, timeout=5000)
                btn = page.locator(btn_selector).first

                if btn.is_visible():
                    print("'Show More' 버튼을 찾아 클릭합니다!")
                    btn.click(force=True)
                    print("클릭 성공! 전체 리스트가 펼쳐질 때까지 5초 대기합니다.")
                    time.sleep(5)
            except Exception as e:
                print("버튼을 누르지 못했습니다. (이미 펼쳐졌거나 에러 발생)")

            # 데이터 추출
            soup = BeautifulSoup(page.content(), "html.parser")
            items = soup.select("li[aria-posinset]")
            print(f"총 {len(items)}개의 FAQ 항목 발견")

            for item in items:
                q_el = item.select_one("h3")
                a_el = item.select_one("div[role='region']")

                if q_el:
                    question = q_el.get_text(strip=True)
                    answer_parts = []

                    if a_el:
                        answer_parts.append(a_el.get_text(separator="\n", strip=True))
                        for img in a_el.find_all("img"):
                            src = img.get("src")
                            if src:
                                full_url = (
                                    f"https://www.volkswagen.co.kr{src}"
                                    if src.startswith("/")
                                    else src
                                )
                                answer_parts.append(f"\n[이미지: {full_url}]")
                        for a_tag in a_el.find_all("a"):
                            href = a_tag.get("href")
                            if href:
                                answer_parts.append(f"\n[링크: {href}]")

                    answer = "\n".join(answer_parts)

                    # [수정됨] 통합 테이블 구조에 맞게 brand='폭스바겐', category='일반 정비/서비스' 기본 지정 및 데이터 수집
                    faq_list.append(
                        FaqItem(
                            brand="폭스바겐",
                            category="일반 정비/서비스",
                            question=question,
                            answer=answer,
                        )
                    )

            browser.close()
        return faq_list


# 4. 결과 검증 보고서 출력
def show_results():
    engine = get_engine()
    with engine.connect() as conn:
        # 통합 DB 내 폭스바겐 데이터만 집계
        total = conn.execute(
            text("SELECT COUNT(*) FROM company_faq WHERE brand = '폭스바겐'")
        ).fetchone()[0]
        by_cat = conn.execute(text("""
            SELECT COALESCE(NULLIF(category,''), '(없음)') AS cat, COUNT(*) AS cnt
            FROM company_faq 
            WHERE brand = '폭스바겐'
            GROUP BY cat 
            ORDER BY cnt DESC
        """)).fetchall()

    print(f"\n{'='*60}")
    print(f"폭스바겐 수집 결과 보고서 | 통합 DB 내 폭스바겐 데이터: {total}건\n")
    print("카테고리별 저장 현황:")
    for row in by_cat:
        print(f"  · {row[0]}: {row[1]}건")
    print(f"{'='*60}")


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────
def run():
    crawler = VWFaqCrawler()
    data = crawler.crawl()
    save_faq_to_db(data)
    print("폭스바겐 크롤링 프로세스 완료!")
    show_results()


if __name__ == "__main__":
    run()
