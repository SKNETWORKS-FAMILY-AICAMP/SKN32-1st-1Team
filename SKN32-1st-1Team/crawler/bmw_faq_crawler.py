# path : crawling\bmw_faq_crawling.py
# BMW Korea FAQ dynamic crawler

from selenium import webdriver as wd
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from dataclasses import dataclass
from dotenv import load_dotenv
import pymysql
import os
import re
import time

load_dotenv()

BMW_FAQ_URL = "https://www.bmw.co.kr/kr/s/?language=ko"

# ================================
# 설정 (통합 DB 및 테이블 지정)
# ================================
MYSQL_HOST = os.getenv("DB_HOST")
MYSQL_PORT = int(os.getenv("DB_PORT"))
MYSQL_DB = os.getenv("DB_NAME")  # ← 통합 DB명 반영
MYSQL_USER = os.getenv("DB_USER")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD")

TABLE_NAME = "company_faq"  # ← 통합 테이블명 반영


@dataclass
class BmwFaq:
    brand: str = "BMW"  # ← 통합 데이터 규격(brand) 추가
    category: str = "미분류"
    question: str = ""
    answer: str = ""
    source_url: str = BMW_FAQ_URL

    def __init__(self, category, question, answer, source_url=BMW_FAQ_URL):
        self.brand = "BMW"
        self.category = category
        self.question = question
        self.answer = answer
        self.source_url = source_url


# ================================
# DB 연결 함수 관리 (자체 구현으로 전환)
# ================================
def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        db=MYSQL_DB,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=False,
    )


def insert_faq_to_db(faq):
    # [수정됨] 복합 유니크 키에 부합하도록 쿼리를 통합 테이블 구조(company_faq)로 변경
    sql = f"""
    INSERT INTO {TABLE_NAME} (brand, category, question, answer)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        category = VALUES(category),
        answer = VALUES(answer)
    """
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (faq.brand, faq.category, faq.question, faq.answer))
            inserted = cursor.rowcount
        conn.commit()
    except Exception as e:
        print(f"❌ DB 저장 오류: {e}", flush=True)
        conn.rollback()
    finally:
        conn.close()
    return inserted


def count_saved_faq():
    conn = get_connection()
    count = 0
    try:
        with conn.cursor() as cursor:
            # 타 브랜드 간섭 방지를 위해 brand='BMW' 조건 추가
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE brand='BMW'")
            count = cursor.fetchone()[0]
    finally:
        conn.close()
    return count


# ================================
# 텍스트 클렌징 및 헬퍼 함수
# ================================
def clean_text(text):
    if text is None:
        return ""
    return " ".join(str(text).replace("\xa0", " ").split())


def clean_answer(text):
    text = clean_text(text)
    remove_phrases = [
        "도움이 되었습니까?",
        "피드백을 보내주셔서 감사합니다.",
        "피드백을 보내주셔서 감사합니다",
    ]
    for phrase in remove_phrases:
        text = text.replace(phrase, " ")
    return clean_text(text)


def clean_category(text):
    text = clean_text(text)
    if not text:
        return "미분류"
    parts = [part.strip() for part in re.split(r"[,/|]+", text) if part.strip()]
    return ", ".join(parts) if parts else "미분류"


# ================================
# 드라이버 및 브라우저 제어 로직
# ================================
def make_driver():
    print("Chrome driver starting...", flush=True)
    options = wd.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    driver = wd.Chrome(options=options)
    driver.set_script_timeout(900)
    print("Chrome driver ready.", flush=True)
    return driver


def accept_cookie_if_exists(driver):
    script = """
    function allElements(root=document, arr=[]) {
      root.querySelectorAll('*').forEach(el => {
        arr.push(el);
        if (el.shadowRoot) allElements(el.shadowRoot, arr);
      });
      return arr;
    }
    function norm(el) {
      return (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
    }
    for (const el of allElements()) {
      const t = norm(el);
      if (t === '모두 수락' || t.includes('모두 수락')) {
        try {
          el.click();
          break;
        } catch (e) {}
      }
    }
    document.querySelectorAll(
      'epaas-consent-drawer-shell, epaas-consent-drawer, .epaas-consent-drawer-shell'
    ).forEach(el => el.remove());
    document.documentElement.style.overflow = 'auto';
    document.body.style.overflow = 'auto';
    const footer = document.querySelector('footer');
    if (footer) footer.style.marginBottom = '0px';
    return true;
    """
    try:
        driver.execute_script(script)
    except Exception:
        pass


def get_article_count(driver):
    script = """
    function allElements(root=document, arr=[]) {
      root.querySelectorAll('*').forEach(el => {
        arr.push(el);
        if (el.shadowRoot) allElements(el.shadowRoot, arr);
      });
      return arr;
    }
    return allElements().filter(el =>
      el.tagName && el.tagName.toLowerCase() === 'c-scp-article-list-item-expandable'
    ).length;
    """
    return int(driver.execute_script(script) or 0)


def click_load_more_once(driver):
    script = """
    function allElements(root=document, arr=[]) {
      root.querySelectorAll('*').forEach(el => {
        arr.push(el);
        if (el.shadowRoot) allElements(el.shadowRoot, arr);
      });
      return arr;
    }
    function norm(el) {
      return (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
    }
    const buttons = allElements().filter(el =>
      el.getAttribute('data-name') === 'loadMoreButton' ||
      norm(el) === '도움말 더 보기'
    );
    if (buttons.length === 0) return false;
    buttons[0].scrollIntoView({block: 'center'});
    buttons[0].click();
    return true;
    """
    accept_cookie_if_exists(driver)
    return bool(driver.execute_script(script))


def click_load_more_until_end(driver, max_clicks=120):
    clicks = 0
    stale_clicks = 0

    while clicks < max_clicks:
        before = get_article_count(driver)
        clicked = click_load_more_once(driver)
        if not clicked:
            break

        clicks += 1
        increased = False
        after = before
        for _ in range(24):
            time.sleep(0.35)
            after = get_article_count(driver)
            if after > before:
                increased = True
                break

        if increased:
            stale_clicks = 0
            print(f"더보기 클릭 {clicks}: {before} -> {after}", flush=True)
            continue

        stale_clicks += 1
        print(f"더보기 클릭 {clicks}: 추가 항목 확인 안 됨({before})", flush=True)
        if stale_clicks >= 3:
            break

    return clicks


def collect_article_by_index(driver, index):
    script = """
    const done = arguments[arguments.length - 1];
    const targetIndex = arguments[0];
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    function allElements(root=document, arr=[]) {
      root.querySelectorAll('*').forEach(el => {
        arr.push(el);
        if (el.shadowRoot) allElements(el.shadowRoot, arr);
      });
      return arr;
    }
    function normText(value) {
      return (value || '').replace(/\\s+/g, ' ').trim();
    }
    function norm(el) {
      return normText(el ? (el.innerText || el.textContent || '') : '');
    }
    function getInner(item) {
      const inner = [];
      allElements(item.shadowRoot || item, inner);
      return inner;
    }
    function getQuestion(inner) {
      const qEl = inner.find(el => (el.className || '').toString().includes('article-headline'));
      return norm(qEl);
    }
    function getPreview(inner) {
      const el = inner.find(node => {
        const cls = (node.className || '').toString();
        return cls.includes('article-preview') || node.getAttribute('data-id') === 'articlePreview';
      });
      return norm(el);
    }
    function getFullHelpButton(inner) {
      const buttons = inner.filter(el => el.tagName === 'BUTTON');
      return buttons.find(button => {
        const cls = (button.className || '').toString();
        const label = button.getAttribute('aria-label') || '';
        const text = norm(button);
        return cls.includes('article_read_full') ||
          text === '전체 도움말 보기' ||
          label.includes('전체 도움말 보기');
      });
    }
    function getCategory(inner, question, preview, answer) {
      const forbidden = new Set([
        question, preview, answer, '전체 도움말 보기', '도움이 되었습니까?', '예', '아니요'
      ]);
      const candidates = inner
        .map(el => {
          const cls = (el.className || '').toString().toLowerCase();
          const dataId = (el.getAttribute('data-id') || '').toLowerCase();
          const text = norm(el);
          return {cls, dataId, text};
        })
        .filter(row => row.text &&
          row.text.length <= 40 &&
          !forbidden.has(row.text) &&
          !row.text.includes(question) &&
          !row.text.includes(preview) &&
          (
            row.cls.includes('tag') ||
            row.cls.includes('label') ||
            row.cls.includes('pill') ||
            row.cls.includes('topic') ||
            row.cls.includes('category') ||
            row.dataId.includes('tag') ||
            row.dataId.includes('category')
          )
        )
        .map(row => row.text);

      return [...new Set(candidates)].join(', ') || '미분류';
    }
    function getAnswerCandidates(inner) {
      return inner
        .filter(el => {
          const cls = (el.className || '').toString();
          return cls.includes('article-detail-container') ||
            cls.includes('article-panel-inner') ||
            cls.includes('article-body') ||
            el.getAttribute('data-id') === 'articleContainer';
        })
        .map(el => norm(el))
        .filter(text => text && text !== '도움이 되었습니까?')
        .sort((a, b) => b.length - a.length);
    }
    function isFullAnswer(answer, preview) {
      if (!answer || answer === '도움이 되었습니까?') return false;
      if (answer.length < 40 && answer.length <= preview.length) return false;
      if (preview && answer === preview) return false;
      return true;
    }

    (async () => {
      const items = allElements().filter(el =>
        el.tagName && el.tagName.toLowerCase() === 'c-scp-article-list-item-expandable'
      );
      const item = items[targetIndex];
      if (!item) {
        done({error: 'item not found'});
        return;
      }

      let inner = getInner(item);
      const question = getQuestion(inner);
      if (!question) {
        done({error: 'question not found'});
        return;
      }

      const preview = getPreview(inner);
      const button = getFullHelpButton(inner);
      if (button) {
        try {
          button.scrollIntoView({block: 'center'});
          button.click();
        } catch (e) {}
      }

      await sleep(1100);

      let answer = '';
      for (let attempt = 0; attempt < 8; attempt += 1) {
        inner = getInner(item);
        const candidates = getAnswerCandidates(inner);
        answer = candidates.length ? candidates[0] : '';
        if (isFullAnswer(answer, preview)) break;
        await sleep(600);
      }

      inner = getInner(item);
      const category = getCategory(inner, question, preview, answer);
      try {
        const closeButton = getFullHelpButton(inner);
        if (closeButton && closeButton.getAttribute('aria-expanded') === 'true') {
          closeButton.click();
        }
      } catch (e) {}
      done({index: targetIndex + 1, category, question, answer, preview});
    })().catch(error => done({error: String(error)}));
    """

    item = driver.execute_async_script(script, index)
    if item.get("error"):
        print(f'{index + 1}번 항목 수집 오류: {item.get("error")}', flush=True)
        return None

    question = clean_text(item.get("question"))
    answer = clean_answer(item.get("answer"))
    category = clean_category(item.get("category"))
    if not question or not answer:
        print(f"{index + 1}번 항목 제외: 질문 또는 답변 없음", flush=True)
        return None
    if question in ["도움이 필요하신가요?", "무엇을 도와드릴까요?"]:
        return None
    return BmwFaq(category, question, answer, BMW_FAQ_URL)


def collect_and_save_articles(driver, total_count):
    saved = 0
    seen_questions = set()

    for index in range(total_count):
        try:
            faq = collect_article_by_index(driver, index)
        except WebDriverException as e:
            print(f"{index + 1}번 항목에서 브라우저 세션 오류로 중단: {e}", flush=True)
            break
        if faq is None:
            continue

        question_key = re.sub(r"\s+", " ", faq.question).strip()
        if question_key in seen_questions:
            continue
        seen_questions.add(question_key)

        # [수정됨] 내부 Model 클래스 의존 대신 자체 함수 호출로 분리 및 로깅 고도화
        db_res = insert_faq_to_db(faq)
        if db_res > 0:
            saved += 1

        if index % 10 == 0 or index == total_count - 1:
            print(f"상세답변 저장 진행: 화면 항목 {index + 1}개 검사 중...", flush=True)

    return saved


# ================================
# 메인 제어문 실행 루프
# ================================
def run():
    driver = make_driver()
    saved_count = 0
    # [수정됨] 기존 데이터를 전체 파괴하는 일괄 delete_all() 호출부는 영구적으로 비활성화(제거)했습니다.

    try:
        print("BMW FAQ 접속 중...", flush=True)
        driver.get(BMW_FAQ_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(8)
        accept_cookie_if_exists(driver)

        initial_count = get_article_count(driver)
        print("초기 FAQ 항목 수:", initial_count, flush=True)
        load_clicks = click_load_more_until_end(driver)
        final_count = get_article_count(driver)
        print("도움말 더보기 클릭 수:", load_clicks, flush=True)
        print("최종 화면 FAQ 항목 수:", final_count, flush=True)

        saved_count = collect_and_save_articles(driver, final_count)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print("\n============================================================")
    print("이번 회차 신규 적재 완료 건수:", saved_count, flush=True)
    print("통합 DB 내 BMW 데이터 총 누적 건수:", count_saved_faq(), flush=True)
    print("============================================================")


if __name__ == "__main__":
    run()
