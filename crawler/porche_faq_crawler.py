# Porsche Korea FAQ crawler
# Source: https://www.porsche.com/korea/ko/faq/

from dataclasses import dataclass
import os
import re
import time

import pymysql
from dotenv import load_dotenv
from selenium import webdriver as wd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()

PORSCHE_FAQ_URL = "https://www.porsche.com/korea/ko/faq/"

MYSQL_HOST = os.getenv("DB_HOST")
MYSQL_PORT = int(os.getenv("DB_PORT"))
MYSQL_DB = os.getenv("DB_NAME")
MYSQL_USER = os.getenv("DB_USER")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD")

TABLE_NAME = "company_faq"  # ← 통합 테이블명 지정


@dataclass
class PorscheFaq:
    brand: str = "포르쉐"  # [수정됨] brand 컬럼 데이터 기본값 지정
    category: str = "미분류"
    question: str = ""
    raw_question: str = ""
    answer: str = ""
    source_url: str = ""


def get_connection(database=MYSQL_DB):
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        db=database,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=False,
    )


def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).replace("\xa0", " ").split())


def split_category_question(raw_question):
    raw_question = clean_text(raw_question)
    match = re.match(r"^\[([^\]]+)\]\s*(.+)$", raw_question)
    if not match:
        return "미분류", raw_question
    return clean_text(match.group(1)), clean_text(match.group(2))


# [수정됨] 개별 porsche_db 및 faq 테이블 생성을 담당하던 로직은 제거했습니다. (이미 테이블이 생성되어 있어야 함)


def insert_faq(faq):
    # [수정됨] 통합 테이블(company_faq) 구조 및 복합 유니크 키에 부합하도록 쿼리 전면 수정
    sql = f"""
  INSERT INTO {TABLE_NAME}
    (brand, category, question, answer)
  VALUES
    (%s, %s, %s, %s)
  ON DUPLICATE KEY UPDATE
    category = VALUES(category),
    answer = VALUES(answer)
  """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (faq.brand, faq.category, faq.question, faq.answer))
        conn.commit()


def count_saved_faq():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # 타사 브랜드와 혼선이 없도록 포르쉐 데이터만 카운트
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE brand='포르쉐'")
            return cursor.fetchone()[0]


def make_driver():
    options = wd.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1400")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    driver = wd.Chrome(options=options)
    driver.set_script_timeout(120)
    return driver


def accept_cookie_if_exists(driver):
    script = """
  function clean(text) {
    return (text || '').replace(/\\s+/g, ' ').trim();
  }
  const candidates = Array.from(document.querySelectorAll('button, a, p-button'))
    .filter(el => {
      const text = clean(el.innerText || el.textContent);
      return text.includes('모두 허용') ||
             text.includes('모두 동의') ||
             text.includes('동의') ||
             text.includes('Accept all');
    });
  for (const el of candidates) {
    try {
      el.click();
      return true;
    } catch (e) {}
  }
  return false;
  """
    try:
        driver.execute_script(script)
        time.sleep(1)
    except Exception:
        pass


def collect_faq_rows(driver):
    script = """
  function clean(text) {
    return (text || '').replace(/\\s+/g, ' ').trim();
  }
  function getAnswer(item, question) {
    const candidates = Array.from(item.querySelectorAll('p-text, div, p'))
      .map(el => clean(el.innerText || el.textContent))
      .filter(text => text && text !== question && !text.includes(question))
      .sort((a, b) => b.length - a.length);
    return candidates.length ? candidates[0] : '';
  }

  const rows = Array.from(document.querySelectorAll('p-accordion'))
    .map(item => {
      const heading = item.querySelector('[slot="heading"]');
      const rawQuestion = clean(heading ? (heading.innerText || heading.textContent) : item.innerText);
      return {
        raw_question: rawQuestion,
        answer: getAnswer(item, rawQuestion),
        source_url: location.href
      };
    })
    .filter(row => row.raw_question && row.answer);

  return rows;
  """
    rows = []
    for item in driver.execute_script(script):
        category, question = split_category_question(item.get("raw_question", ""))
        answer = clean_text(item.get("answer", ""))
        if not question or not answer:
            continue
        rows.append(
            PorscheFaq(
                brand="포르쉐",  # [수정됨] 고정식 brand 정보 주입
                category=category,
                question=question,
                raw_question=clean_text(item.get("raw_question")),
                answer=answer,
                source_url=PORSCHE_FAQ_URL,
            )
        )
    return rows


def run():
    # [수정됨] 초기 데이터베이스 구축 및 전체 삭제(delete_all) 로직 호출부 제거
    driver = make_driver()
    try:
        print("포르쉐 FAQ 접속 중...", flush=True)
        driver.get(PORSCHE_FAQ_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(8)
        accept_cookie_if_exists(driver)

        faq_rows = collect_faq_rows(driver)
        print("수집 FAQ 건수:", len(faq_rows), flush=True)

        for faq in faq_rows:
            insert_faq(faq)

    finally:
        driver.quit()

    print("통합 DB 내 포르쉐 데이터 저장 건수:", count_saved_faq(), flush=True)


if __name__ == "__main__":
    run()
