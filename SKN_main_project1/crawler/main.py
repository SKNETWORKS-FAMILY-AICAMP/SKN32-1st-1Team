"""
전체 브랜드 FAQ 크롤링 통합 실행
  순서: 현대 → 기아 → 제네시스 → BMW → 포르쉐 → 캐딜락 → 쉐보레 → 폭스바겐
  저장: car_project_db.company_faq (brand, category, question, answer)
"""

import logging
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()

# ── 로그 설정 (각 모듈 import 전에 먼저 설정해야 basicConfig 충돌 방지)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("main_crawl.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "homework"),
    "password": os.getenv("DB_PASSWORD", "playdatahomework80"),
    "charset": "utf8mb4",
}
DB_NAME = os.getenv("DB_NAME", "car_project_db")


def init_company_faq():
    """car_project_db 및 company_faq 테이블이 없으면 생성"""
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{DB_NAME}`")
    cur.execute("DROP TABLE IF EXISTS company_faq")
    cur.execute("""
        CREATE TABLE company_faq (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            brand      VARCHAR(50),
            category   VARCHAR(100),
            question   TEXT,
            answer     MEDIUMTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_brand_question (brand(50), question(200))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()
    cur.close()
    conn.close()
    log.info(f"DB `{DB_NAME}`.company_faq 준비 완료")


# ── 크롤러 모듈 import (로그 설정 이후에 import)
import hyundai_faq_crawler
import kia_faq_crawler
import genesis_faq_crawler
import bmw_faq_crawler
import porche_faq_crawler
import cadillac_faq_crawler
import chevrolet_faq_crawler
import volkswagen_faq_crawler

CRAWLERS = [
    ("현대자동차", hyundai_faq_crawler),
    ("기아자동차", kia_faq_crawler),
    ("제네시스", genesis_faq_crawler),
    ("BMW", bmw_faq_crawler),
    ("포르쉐", porche_faq_crawler),
    ("캐딜락", cadillac_faq_crawler),
    ("쉐보레", chevrolet_faq_crawler),
    ("폭스바겐", volkswagen_faq_crawler),
]


if __name__ == "__main__":
    # 1. 공통 테이블 준비
    init_company_faq()

    # 2. 각 브랜드 순차 크롤링
    success, failed = [], []
    for brand_name, module in CRAWLERS:
        log.info("\n" + "=" * 60)
        log.info(f"[{brand_name}] 크롤링 시작")
        log.info("=" * 60)
        try:
            module.run()
            success.append(brand_name)
            log.info(f"[{brand_name}] 완료")
        except Exception as e:
            log.error(f"[{brand_name}] 실패: {e}", exc_info=True)
            failed.append(brand_name)

    # 3. 최종 결과 요약
    log.info("\n" + "=" * 60)
    log.info(f"전체 크롤링 완료 — 성공: {len(success)}개 / 실패: {len(failed)}개")
    if success:
        log.info(f"  성공: {', '.join(success)}")
    if failed:
        log.warning(f"  실패: {', '.join(failed)}")
    log.info("=" * 60)
