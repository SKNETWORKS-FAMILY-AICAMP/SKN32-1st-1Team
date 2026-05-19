"""
전체 브랜드 FAQ 크롤링 통합 실행
  순서: 현대 → 기아 → 제네시스 → BMW → 포르쉐 → 캐딜락 → 쉐보레 → 폭스바겐
  저장: car_project_db.company_faq (brand, category, question, answer)
"""

import logging
import pymysql
import os
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
    # .env에 DB_HOST가 없으면 기본값으로 "localhost" 사용
    "host": os.getenv("DB_HOST"),
    # 포트 번호는 문자열로 읽히므로 int()를 통해 정수형으로 안전하게 변환 (기본값 3306)
    "port": int(os.getenv("DB_PORT")),
    # .env에 DB_USER가 없으면 기본값으로 "homework" 사용
    "user": os.getenv("DB_USER"),
    # .env에 DB_PASSWORD가 없으면 기본값으로 "playdatahomework80" 사용
    "password": os.getenv("DB_PASSWORD"),
    # 통합 데이터베이스명 설정 (.env의 DB_NAME 혹은 DB_DATABASE 매핑 가능)
    "database": os.getenv("DB_NAME"),
    # 이모지 및 다국어 지원을 위한 인코딩 설정
    "charset": "utf8mb4",
    # 데이터 안정성을 위해 오토커밋은 기본적으로 비활성화 (필요시 True 변경)
    "autocommit": False,
}


def check_company_faq():
    """기존 car_project_db.company_faq 테이블 연결 확인"""
    db_name = DB_CONFIG["database"]

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    # ⚠️ DROP 및 CREATE 모두 제거 완료
    # 기존 데이터베이스 및 테이블이 정상적으로 존재하는지만 체크합니다.
    cur.execute(f"USE `{db_name}`")
    cur.execute("SELECT 1 FROM company_faq LIMIT 1")

    cur.close()
    conn.close()
    log.info(
        f"기존 DB `{db_name}`.company_faq 테이블 연결 성공 (데이터 insert 준비 완료)"
    )


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
    # 1. 기존 테이블 연결 및 상태 확인
    try:
        check_company_faq()
    except Exception as e:
        log.error(f"DB 연결 실패 (테이블이 존재하지 않거나 설정 오류): {e}")
        exit(1)

    # 2. 각 브랜드 순차 크롤링 (기존 테이블에 insert)
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
