from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import pymysql
import os
import time

load_dotenv()

# ================================
# 설정 (통합 DB 및 테이블 지정)
# ================================
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
}

TABLE_NAME = "company_faq"  # ← 통합 테이블명으로 변경

FAQ_URLS = [
    {
        "category": "구매관련",
        "url": "https://www.chevrolet.co.kr/faq/purchasing-related",
    },
    {
        "category": "차량관리",
        "url": "https://www.chevrolet.co.kr/faq/product-maintenance",
    },
    {"category": "오토카드", "url": "https://www.chevrolet.co.kr/faq/autocard"},
    {
        "category": "통합계정및홈페이지",
        "url": "https://www.chevrolet.co.kr/faq/website",
    },
    {
        "category": "장애인차량",
        "url": "https://www.chevrolet.co.kr/faq/disabled-vehicles",
    },
    {"category": "마이링크", "url": "https://www.chevrolet.co.kr/faq/mylink"},
    {"category": "내비업데이트", "url": "https://www.chevrolet.co.kr/faq/navigation"},
    {
        "category": "CarPlay",
        "url": "https://www.chevrolet.co.kr/faq/android-auto-apple-carplay",
    },
    {"category": "OnlineShop", "url": "https://www.chevrolet.co.kr/faq/online-shop"},
    {"category": "EV리콜", "url": "https://www.chevrolet.co.kr/faq/ev-recall"},
]

# CSS 셀렉터
Q_SELECTOR = "div.col-con gb-expander div.gb-expander-btn.stat-expand-icon h6, div.col-con gb-expander div.gb-expander-btn.stat-expand-icon h6.gb-expander-headline"
A_SELECTOR = "gb-expander.active div.gb-expander-content div div div p"

# [수정됨] 기존 테이블 생성 로직(create_table) 제거 (이미 테이블이 생성되어 있어야 함)


# ================================
# Selenium 드라이버 설정
# ================================
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # 크롤링 안정성을 위해 헤드리스 활성화
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


# ================================
# FAQ 크롤링
# ================================
def crawl_faq(driver, category, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-con"))
        )
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "gb-adv-grid.gb-large-margin")
                )
            )
        except:
            pass
        time.sleep(3)

        results = []

        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        for scroll_pos in range(0, last_height, 300):
            driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
            time.sleep(0.2)

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        driver.execute_script("""
            document.querySelectorAll('gb-expander').forEach(function(el) {
                el.scrollIntoView();
            });
        """)
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        question_elements = driver.find_elements(By.CSS_SELECTOR, Q_SELECTOR)
        print(f"  [{category}] 질문 {len(question_elements)}개 발견")

        for q_el in question_elements:
            q_text = q_el.text.strip()
            if not q_text:
                continue

            driver.execute_script("arguments[0].scrollIntoView(true);", q_el)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", q_el)
            time.sleep(0.8)

            try:
                a_elements = driver.find_elements(By.CSS_SELECTOR, A_SELECTOR)
                answer_texts = [p.text.strip() for p in a_elements if p.text.strip()]
                answer = "\n".join(answer_texts)
            except:
                answer = ""

            results.append({"category": category, "question": q_text, "answer": answer})

            driver.execute_script("arguments[0].click();", q_el)
            time.sleep(0.3)

        print(f"  [{category}] {len(results)}개 수집 완료")
        return results

    except Exception as e:
        print(f"  [{category}] 오류: {e}")
        return []


# ================================
# DB 저장
# ================================
def save_to_db(conn, items):
    cursor = conn.cursor()
    # [수정됨] 통합 테이블 구조(brand 포함) 및 중복 방지를 위한 INSERT IGNORE 구문 사용
    sql = f"INSERT IGNORE INTO {TABLE_NAME} (brand, category, question, answer) VALUES (%s, %s, %s, %s)"

    for item in items:
        # [수정됨] brand 컬럼 데이터로 '쉐보레' 문자열 주입
        cursor.execute(
            sql, ("쉐보레", item["category"], item["question"], item["answer"])
        )

    inserted = cursor.rowcount
    conn.commit()
    skipped = len(items) - inserted
    print(f"  -> 통합 테이블 반영: {inserted}건 삽입 / {skipped}건 중복 스킵")


# ================================
# 메인 실행
# ================================
def main():
    conn = pymysql.connect(**DB_CONFIG)

    driver = get_driver()
    print("브라우저 시작 (Headless 모드)\n")

    total = 0
    for faq in FAQ_URLS:
        print(f"크롤링 중: {faq['category']} ({faq['url']})")
        items = crawl_faq(driver, faq["category"], faq["url"])
        if items:
            save_to_db(conn, items)
            total += len(items)
        time.sleep(1)

    driver.quit()

    print(f"\n완료! 총 {total}개 FAQ 처리 완료")

    # [수정됨] 다른 브랜드와 섞이지 않도록 쉐보레 전용 데이터 조건 추가
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT category, COUNT(*) as cnt FROM {TABLE_NAME} WHERE brand = '쉐보레' GROUP BY category"
    )
    print("\n[통합 DB 내 쉐보레 카테고리별 저장 현황]")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}개")

    conn.close()


def run():
    main()


if __name__ == "__main__":
    run()
