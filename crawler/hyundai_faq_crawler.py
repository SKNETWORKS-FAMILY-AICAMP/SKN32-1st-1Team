import time
import logging
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
TARGET_URL = "https://www.hyundai.com/kr/ko/e/customer/center/faq"
TARGET_URL_2 = "https://www.hyundai.com/kr/ko/faq.html"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "charset": "utf8mb4",
    "autocommit": False,
}

DB_NAME = os.getenv("DB_NAME", "car_project_db")
TABLE_NAME = "company_faq"

# ──────────────────────────────────────────────
# 로깅
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("hyundai_faq_crawl.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# DB 유틸
# ──────────────────────────────────────────────
# [수정됨] 기존 테이블을 새로 생성하는 init_db() 로직은 삭제했습니다.


def save_to_db(faq_list: list[tuple]):
    """faq_list → DB 일괄 INSERT (brand='현대' 컬럼 추가 반영)"""
    conn = pymysql.connect(**DB_CONFIG, db=DB_NAME)
    cur = conn.cursor()

    # [수정됨] 수집된 데이터 앞에 '현대' 가 들어가도록 튜플 재가공
    final_data = [
        ("현대", category, question, answer) for category, question, answer in faq_list
    ]

    # [수정됨] 통합 테이블 구조(brand 포함)에 맞춤형 INSERT IGNORE 실행
    sql = f"INSERT IGNORE INTO `{TABLE_NAME}` (brand, category, question, answer) VALUES (%s, %s, %s, %s)"
    cur.executemany(sql, final_data)
    inserted = cur.rowcount
    conn.commit()
    skipped = len(faq_list) - inserted
    log.info(f"DB 저장 완료: {inserted}건 삽입 / {skipped}건 중복 스킵")
    cur.close()
    conn.close()


# ──────────────────────────────────────────────
# WebDriver 유틸
# ──────────────────────────────────────────────
def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1080,960")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_argument("--headless=new")  # 백그라운드 크롤링을 위해 헤드리스 활성화

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )
    return driver


def safe_click(driver: webdriver.Chrome, element):
    """ElementClickInterceptedException 방어 클릭"""
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", element)


def wait_loading(sec: float = 1.5):
    time.sleep(sec)


# ──────────────────────────────────────────────
# 크롤링 핵심 함수
# ──────────────────────────────────────────────
def get_answer(item_elem) -> str:
    """div.conts 안의 텍스트 전체 추출"""
    try:
        conts = item_elem.find_element(By.CSS_SELECTOR, "div.conts")
        return conts.text.strip()
    except NoSuchElementException:
        return ""


def scrape_page_items(driver: webdriver.Chrome, tab_name: str) -> list[tuple]:
    """현재 페이지의 list-item 전부 순회 → [(category, question, answer), ...]"""
    results = []

    list_items = driver.find_elements(By.CSS_SELECTOR, "div.list-wrap div.list-item")
    if not list_items:
        log.warning("    list-item 없음")
        return results

    log.info(f"    항목 수: {len(list_items)}")

    for idx in range(len(list_items)):
        try:
            list_items = driver.find_elements(
                By.CSS_SELECTOR, "div.list-wrap div.list-item"
            )
            item = list_items[idx]

            item_class = item.get_attribute("class") or ""
            if "active" in item_class:
                log.debug(f"      [{idx+1}] 이미 열린 상태 — 클릭 생략")
            else:
                btn = item.find_element(By.TAG_NAME, "button")
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn
                )
                safe_click(driver, btn)
                wait_loading(0.8)

            list_items = driver.find_elements(
                By.CSS_SELECTOR, "div.list-wrap div.list-item"
            )
            item = list_items[idx]

            try:
                category = (
                    item.find_element(By.CSS_SELECTOR, "span.list-category")
                    .text.strip()
                    .strip("[")
                    .strip("]")
                    .strip()
                )
            except NoSuchElementException:
                category = tab_name

            try:
                question = item.find_element(
                    By.CSS_SELECTOR, "span.list-content"
                ).text.strip()
            except NoSuchElementException:
                question = ""

            answer = get_answer(item)

            if question:
                results.append((category, question, answer))
                log.info(
                    f"      [{idx+1}] {category} | {question[:45]}{'...' if len(question)>45 else ''}"
                )
            else:
                log.warning(f"      [{idx+1}] question 없음, 스킵")

        except StaleElementReferenceException:
            log.warning(f"      [{idx+1}] StaleElement — 스킵")
        except Exception as e:
            log.warning(f"      [{idx+1}] 오류: {e}")

    return results


def has_next_page(driver: webdriver.Chrome) -> bool:
    """현재 활성 페이지 번호 뒤에 다음 li가 있으면 True"""
    try:
        pager = driver.find_element(By.CSS_SELECTOR, "ul.el-pager")
        all_li = pager.find_elements(By.CSS_SELECTOR, "li.number")
        active_i = next(
            (i for i, li in enumerate(all_li) if "active" in li.get_attribute("class")),
            None,
        )
        return active_i is not None and active_i < len(all_li) - 1
    except NoSuchElementException:
        return False


def click_next_page(driver: webdriver.Chrome):
    next_btn = driver.find_element(By.CSS_SELECTOR, "button.btn.btn-next")
    safe_click(driver, next_btn)
    wait_loading(2.0)


# ──────────────────────────────────────────────
# 메인 크롤러
# ──────────────────────────────────────────────
def crawl() -> list[tuple]:
    faq_list: list[tuple] = []
    driver = build_driver()
    wait = WebDriverWait(driver, 20)

    try:
        log.info(f"접속: {TARGET_URL}")
        driver.get(TARGET_URL)
        wait_loading(3.0)

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.tab-menu__icon-wrapper")
            )
        )
        all_li = driver.find_elements(By.CSS_SELECTOR, "ul.tab-menu__icon-wrapper li")
        category_count = len(all_li)
        for i, li in enumerate(all_li):
            try:
                txt = li.find_element(By.TAG_NAME, "button").text.strip()
                if txt == "전체":
                    category_count = i
                    break
            except NoSuchElementException:
                pass
        log.info(
            f"카테고리 탭: {category_count}개 (전체 li: {len(all_li)}개, 서브필터 제외)"
        )

        for tab_idx in range(category_count):
            tabs = driver.find_elements(By.CSS_SELECTOR, "ul.tab-menu__icon-wrapper li")
            tab_btn = tabs[tab_idx].find_element(By.TAG_NAME, "button")
            tab_name = tab_btn.text.strip() or f"Tab{tab_idx+1}"

            log.info(f"\n{'='*55}")
            log.info(f"탭 [{tab_idx+1}/{category_count}]: {tab_name}")

            safe_click(driver, tab_btn)
            wait_loading(2.0)

            page = 1
            while True:
                log.info(f"  ── 페이지 {page}")

                try:
                    wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.list-wrap")
                        )
                    )
                except TimeoutException:
                    log.warning("  list-wrap 로딩 실패 → 다음 탭")
                    break

                page_data = scrape_page_items(driver, tab_name)
                faq_list.extend(page_data)
                log.info(
                    f"  ── 이 페이지 {len(page_data)}건 수집 (누적: {len(faq_list)}건)"
                )

                if has_next_page(driver):
                    click_next_page(driver)
                    page += 1
                else:
                    log.info("  마지막 페이지 → 다음 탭으로")
                    break

        log.info(f"\n첫 번째 URL 크롤링 완료 — 총 {len(faq_list)}건 수집")

    except Exception as e:
        log.error(f"크롤링 중 치명적 오류: {e}", exc_info=True)

    finally:
        driver.quit()

    return faq_list


# ──────────────────────────────────────────────
# 두 번째 URL 크롤링 함수
# ──────────────────────────────────────────────
def _inner_text(elem) -> str:
    try:
        val = elem.get_attribute("innerText")
        return val.strip() if val else elem.text.strip()
    except Exception:
        return elem.text.strip()


def scrape_page_items_v2(driver: webdriver.Chrome) -> list[tuple]:
    results = []

    try:
        accordion = driver.find_element(By.CSS_SELECTOR, "div.ui_accordion.acc_01")
    except NoSuchElementException:
        log.warning("    ui_accordion.acc_01 없음")
        return results

    dl_list = accordion.find_elements(By.TAG_NAME, "dl")
    if not dl_list:
        log.warning("    dl 없음")
        return results

    log.info(f"    dl 수: {len(dl_list)}")

    for idx, dl in enumerate(dl_list):
        try:
            try:
                i_elem = dl.find_element(By.CSS_SELECTOR, "b.title i")
                raw_cat = _inner_text(i_elem)
                category = raw_cat.split(">")[0].strip().strip("[").strip("]").strip()
            except NoSuchElementException:
                category = ""

            try:
                brief_elem = dl.find_element(By.CSS_SELECTOR, "span.brief")
                question = _inner_text(brief_elem)
            except NoSuchElementException:
                question = ""

            try:
                exp_elem = dl.find_element(By.CSS_SELECTOR, "dd div.exp")
                answer = _inner_text(exp_elem)
            except NoSuchElementException:
                answer = ""

            if question:
                results.append((category, question, answer))
                log.info(
                    f"      [{idx+1}] {category} | {question[:45]}{'...' if len(question)>45 else ''}"
                )
            else:
                log.warning(f"      [{idx+1}] question 없음, 스킵")

        except StaleElementReferenceException:
            log.warning(f"      [{idx+1}] StaleElement — 스킵")
        except Exception as e:
            log.warning(f"      [{idx+1}] 오류: {e}")

    return results


def has_next_page_v2(driver: webdriver.Chrome) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR, "nav.pagination button.navi.next.disabled")
        return False
    except NoSuchElementException:
        pass
    try:
        driver.find_element(By.CSS_SELECTOR, "nav.pagination button.navi.next")
        return True
    except NoSuchElementException:
        return False


def click_next_page_v2(driver: webdriver.Chrome):
    next_btn = driver.find_element(By.CSS_SELECTOR, "nav.pagination button.navi.next")
    safe_click(driver, next_btn)
    wait_loading(2.0)


def crawl_v2() -> list[tuple]:
    faq_list: list[tuple] = []
    driver = build_driver()
    wait = WebDriverWait(driver, 20)

    try:
        log.info(f"접속: {TARGET_URL_2}")
        driver.get(TARGET_URL_2)
        wait_loading(3.0)

        page = 1
        while True:
            log.info(f"  ── 페이지 {page}")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.ui_accordion.acc_01")
                    )
                )
            except TimeoutException:
                log.warning("  ui_accordion.acc_01 로딩 실패 → 크롤링 종료")
                break

            page_data = scrape_page_items_v2(driver)
            faq_list.extend(page_data)
            log.info(
                f"  ── 이 페이지 {len(page_data)}건 수집 (누적: {len(faq_list)}건)"
            )

            if has_next_page_v2(driver):
                click_next_page_v2(driver)
                page += 1
            else:
                log.info("  마지막 페이지 → 크롤링 종료")
                break

        log.info(f"\n두 번째 URL 크롤링 완료 — 총 {len(faq_list)}건 수집")

    except Exception as e:
        log.error(f"두 번째 URL 크롤링 중 치명적 오류: {e}", exc_info=True)

    finally:
        driver.quit()

    return faq_list


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────
def run():
    log.info("\n" + "=" * 60)
    log.info("=== 현대 첫 번째 URL 크롤링 시작 ===")
    log.info("=" * 60)
    faq_list = crawl()
    if faq_list:
        save_to_db(faq_list)
    else:
        log.warning("첫 번째 URL: 수집된 데이터 없어 DB 저장 생략")

    log.info("\n" + "=" * 60)
    log.info("=== 현대 두 번째 URL 크롤링 시작 ===")
    log.info("=" * 60)
    faq_list_2 = crawl_v2()
    if faq_list_2:
        save_to_db(faq_list_2)
        log.info("현대 크롤링 완료!")
    else:
        log.warning("두 번째 URL: 수집된 데이터 없어 DB 저장 생략")


if __name__ == "__main__":
    run()
