import time
import os
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "car_project_db"
TABLE_NAME = "company_faq"


def get_engine(with_db: bool = True):
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "homework")
    password = os.getenv("DB_PASSWORD", "playdatahomework80")
    database = os.getenv("DB_NAME", DB_NAME)
    db_part = f"/{database}" if with_db else ""
    db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}{db_part}?charset=utf8mb4"
    return create_engine(db_url)


@dataclass
class FaqItem:
    category: str
    question: str
    answer: str
    brand: str = "기아자동차"
    crawled_at: datetime = None


def save_faq_to_db(faq_items):
    if not faq_items:
        print("저장할 데이터가 없습니다.")
        return
    engine = get_engine()
    with engine.connect() as conn:
        sql = text(f"""
            INSERT IGNORE INTO `{TABLE_NAME}` (brand, category, question, answer)
            VALUES (:brand, :category, :question, :answer)
        """)
        inserted = 0
        for item in faq_items:
            result = conn.execute(sql, {
                "brand":    item.brand,
                "category": item.category,
                "question": item.question,
                "answer":   item.answer,
            })
            inserted += result.rowcount
        conn.commit()
    skipped = len(faq_items) - inserted
    print(f"총 {len(faq_items)}건 처리: {inserted}건 삽입 / {skipped}건 중복 스킵")


# [crawler.py 로직 유지 + 보강]
class KiaFaQCrawler:
    def __init__(self):
        self.url = "https://www.kia.com/kr/customer-service/center/faq"
        self.categories = [
            "차량 구매",
            "차량 정비",
            "기아멤버스",
            "홈페이지",
            "PBV",
            "기타",
        ]

    def crawl(self):
        faq_list = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1280, "height": 1024})
            page = context.new_page()

            print(f"접속: {self.url}")
            page.goto(self.url, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            for cate in self.categories:
                print(f"[{cate}] 수집 시작...")
                try:
                    target_tab = page.locator("button.tabs__btn").filter(has_text=cate)
                    target_tab.scroll_into_view_if_needed()
                    target_tab.click(force=True)
                    time.sleep(3)
                except:
                    continue

                current_page = 1
                while True:
                    page.wait_for_selector(".cmp-accordion__item", timeout=10000)
                    time.sleep(2)

                    soup = BeautifulSoup(page.content(), "html.parser")
                    items = soup.select(".cmp-accordion__item")
                    print(f"   {current_page}페이지: {len(items)}개 분석")

                    for item in items:
                        q_el = item.select_one(".cmp-accordion__title")
                        a_el = item.select_one(
                            ".cmp-accordion__panel"
                        )  # 발견하신 패널 태그

                        if q_el:
                            question = q_el.get_text(strip=True)

                            # 피드백 반영: 여러 줄 텍스트 + 이미지 URL 동시 추출
                            ans_parts = []
                            if a_el:
                                ans_parts.append(
                                    a_el.get_text(separator="\n", strip=True)
                                )
                                for img in a_el.find_all("img"):
                                    src = img.get("src")
                                    if src:
                                        full_url = (
                                            f"https://www.kia.com{src}"
                                            if src.startswith("/")
                                            else src
                                        )
                                        ans_parts.append(f"\n[이미지 경로: {full_url}]")

                            answer = "\n".join(ans_parts)
                            faq_list.append(
                                FaqItem(
                                    category=cate,
                                    question=question,
                                    answer=answer,
                                    crawled_at=datetime.now(),
                                )
                            )

                    # --- [사용자님께서 검증하신 페이지네이션 로직 그대로 적용] ---
                    next_page_num = current_page + 1
                    # 1. 숫자 버튼 먼저 찾기
                    next_btn = page.locator(".paging-list a").filter(
                        has_text=str(next_page_num)
                    )

                    if next_btn.count() > 0:
                        print(f"   {next_page_num}페이지 클릭")
                        next_btn.scroll_into_view_if_needed()
                        next_btn.click(force=True)
                        current_page += 1
                        time.sleep(3)
                    else:
                        # 2. 숫자가 없으면 '다음' 화살표 버튼 클릭 (pagigation-btn-next)
                        next_arrow = page.locator("button.pagigation-btn-next")
                        if next_arrow.count() > 0 and next_arrow.is_visible():
                            print(f"   현재 구간(1-5) 종료, 화살표 클릭")
                            next_arrow.scroll_into_view_if_needed()
                            next_arrow.click(force=True)
                            current_page += 1
                            time.sleep(3)
                        else:
                            print(f"   [{cate}] 수집 완료")
                            break
            browser.close()
        return faq_list


def run():
    crawler = KiaFaQCrawler()
    data = crawler.crawl()
    save_faq_to_db(data)


if __name__ == "__main__":
    run()
