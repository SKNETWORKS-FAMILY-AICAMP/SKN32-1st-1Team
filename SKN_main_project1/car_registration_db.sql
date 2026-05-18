-- ============================================================
--  전국 자동차 등록 현황 & 기업 FAQ 조회 시스템
--  DB 스키마 (MySQL 8.0+ 기준)
--  소나기 팀 | 2026
-- ============================================================
--  [적재 전략]
--  - 매월 새 엑셀 파일을 받아 year_months(YYYYMM) 컬럼으로 구분 적재
--  - 19번 시트(연도별 현황)는 year 컬럼으로 장기 트렌드 관리
--  - FAQ 테이블은 company_config의 is_active로 크롤링 활성화 제어
-- ============================================================

CREATE DATABASE IF NOT EXISTS sknmainproject1_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE sknmainproject1_db;


-- ============================================================
-- [1] 연도별 자동차 등록 현황  (시트 19)
--     2007~현재 연간 집계 — 장기 트렌드 분석 핵심 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS car_yearly_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    stat_year     YEAR            NOT NULL COMMENT '통계 연도 (예: 2024)',

    -- 차종
    car_type      ENUM(
                    '승용', '승합', '화물', '특수','합계'
                  )               NOT NULL COMMENT '차종 구분',

    -- 용도
    usage_type    ENUM(
                    '관용', '자가용', '영업용', '합계'
                  )               NOT NULL COMMENT '용도 구분',

    -- 등록 대수
    registered_count  BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_yearly (stat_year, car_type, usage_type),
    INDEX idx_year      (stat_year),
    INDEX idx_car_type  (car_type)
) ENGINE=InnoDB COMMENT='연도별 자동차 등록 현황 (시트19)';


-- ============================================================
-- [2] 월별 시도별 등록 현황  (시트 01)
--     월 단위 적재 기준 테이블 — 지역별 현황 + 증감 분석
-- ============================================================
CREATE TABLE IF NOT EXISTS car_region_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM (예: 202604)',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명 (예: 서울, 경기)',

    -- 차종
    car_type      ENUM(
                    '승용', '승합', '화물', '특수', '합계'
                  )               NOT NULL COMMENT '차종 구분',

    -- 용도별 등록 대수
    cnt_official  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '관용',
    cnt_private   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '자가용',
    cnt_business  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '영업용',
    cnt_total     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '계',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_region (year_months, region, car_type),
    INDEX idx_ym        (year_months),
    INDEX idx_region    (region),
    INDEX idx_car_type  (car_type)
) ENGINE=InnoDB COMMENT='월별 시도별 등록 현황 (시트01)';


-- ============================================================
-- [3] 연료별 등록 현황  (시트 10)
--     전기·수소·하이브리드 트렌드 핵심 — FAQ 키워드 연계 핵심
-- ============================================================
CREATE TABLE IF NOT EXISTS car_fuel_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명 (합계 포함)',

    -- 연료 종류
    fuel_type     ENUM(
                    '휘발유', '경유', '엘피지', '전기', '수소', '수소전기',
                    'CNG', 'LNG', '등유', '알코올', '태양열',
                    '하이브리드(휘발유+전기)', '하이브리드(경유+전기)',
                    '하이브리드(LPG+전기)', '하이브리드(CNG+전기)',
                    '하이브리드(LNG+전기)', '기타연료'
                  )               NOT NULL COMMENT '연료 종류',

    -- 차종
    car_type      ENUM(
                    '승용', '승합', '화물', '특수', '소계'
                  )               NOT NULL COMMENT '차종',

    -- 용도
    usage_type    ENUM(
                    '비사업용', '사업용', '계'
                  )               NOT NULL COMMENT '용도',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_fuel (year_months, region, fuel_type, car_type, usage_type),
    INDEX idx_ym        (year_months),
    INDEX idx_fuel      (fuel_type),
    INDEX idx_car_type  (car_type)
) ENGINE=InnoDB COMMENT='연료별 등록 현황 (시트10) — 전기·수소 트렌드 분석 핵심';


-- ============================================================
-- [4] 성별·연령별 등록 현황  (시트 04)
--     구매층 인구통계 분석용
-- ============================================================
CREATE TABLE IF NOT EXISTS car_gender_age_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명 (총계 포함)',

    gender        ENUM(
                    '남성', '여성', '기타'
                  )               NOT NULL COMMENT '성별 (기타=법인·사업자)',

    age_group     ENUM(
                    '10대이하', '20대', '30대', '40대',
                    '50대', '60대', '70대', '80대', '90대이상',
                    '법인및사업자', '계'
                  )               NOT NULL COMMENT '연령대',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_gender_age (year_months, region, gender, age_group),
    INDEX idx_ym         (year_months),
    INDEX idx_gender     (gender),
    INDEX idx_age_group  (age_group)
) ENGINE=InnoDB COMMENT='성별·연령별 등록 현황 (시트04)';


-- ============================================================
-- [5] 차종별 유형별 등록 현황  (시트 09)
--     경형·소형·중형·대형·다목적 구분 — 차급 트렌드 분석
-- ============================================================
CREATE TABLE IF NOT EXISTS car_type_detail_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명',

    car_type      ENUM(
                    '승용', '승합', '화물', '특수'
                  )               NOT NULL COMMENT '차종',

    -- 유형 (승용: 일반/승용겸화물/다목적/기타, 화물: 일반/덤프/밴/특수용도형 등)
    car_subtype   VARCHAR(30)     NOT NULL COMMENT '세부유형 (예: 일반, 다목적, 덤프, 견인)',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_type_detail (year_months, region, car_type, car_subtype),
    INDEX idx_ym          (year_months),
    INDEX idx_car_type    (car_type),
    INDEX idx_car_subtype (car_subtype)
) ENGINE=InnoDB COMMENT='차종별 세부유형 현황 (시트09) — 다목적·SUV 트렌드';


-- ============================================================
-- [6] 배기량별 등록 현황 (승용차)  (시트 12)
--     배기량 구간·국산/외산·전기차 분포
-- ============================================================
CREATE TABLE IF NOT EXISTS car_displacement_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명',

    displacement  ENUM(
                    '1000미만', '1000이상1600미만',
                    '1600이상2000미만', '2000이상2500미만',
                    '2500이상', '저속전기차', '전기차'
                  )               NOT NULL COMMENT '배기량 구간',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_displacement (year_months, region, displacement),
    INDEX idx_ym           (year_months),
    INDEX idx_displacement (displacement)
) ENGINE=InnoDB COMMENT='배기량별 승용차 등록 현황 (시트12)';


-- ============================================================
-- [7] 신규 등록 현황 (당월)  (시트 20)
--     신조차·수입차·부활차 구분 — 당월 신차 트렌드
-- ============================================================
CREATE TABLE IF NOT EXISTS car_new_registration (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    region        VARCHAR(20)     NOT NULL COMMENT '시도명',

    car_type      ENUM(
                    '승용', '승합', '화물', '특수', '합계'
                  )               NOT NULL COMMENT '차종',

    reg_type      ENUM(
                    '신조차', '수입차', '부활차', '계'
                  )               NOT NULL COMMENT '등록 구분',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '신규 등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_new_reg (year_months, region, car_type, reg_type),
    INDEX idx_ym       (year_months),
    INDEX idx_reg_type (reg_type)
) ENGINE=InnoDB COMMENT='당월 신규 등록 현황 (시트20) — 수입차 비중 트렌드';


-- ============================================================
-- [8] 차령별 등록 현황  (시트 15)
--     모델연도별 잔존 차량 분포 — 노후화·교체 수요 분석
-- ============================================================
CREATE TABLE IF NOT EXISTS car_age_stats (
    id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    year_months    CHAR(6)         NOT NULL COMMENT '조회년월 YYYYMM',
    model_year    YEAR            NOT NULL COMMENT '차량 모델연도',

    car_type      ENUM(
                    '승용', '승합', '화물', '특수', '합계'
                  )               NOT NULL COMMENT '차종',

    usage_type    ENUM(
                    '관용', '자가용', '영업용', '계'
                  )               NOT NULL COMMENT '용도',

    registered_count  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '등록 대수',

    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_car_age (year_months, model_year, car_type, usage_type),
    INDEX idx_ym         (year_months),
    INDEX idx_model_year (model_year),
    INDEX idx_car_type   (car_type)
) ENGINE=InnoDB COMMENT='차령별 등록 현황 (시트15) — 노후차 교체 수요 분석';


-- ============================================================
-- [9] 파일 적재 이력  (load_to_db.py 중복 방지용)
--     trend_analysis_queries.sql 의 @latest_ym 산출 기준 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS load_history (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    year_months  CHAR(6)      NOT NULL COMMENT '적재 기준 년월 YYYYMM',
    filename     VARCHAR(200) NOT NULL,
    loaded_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_count    INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ym (year_months)
) ENGINE=InnoDB COMMENT='엑셀 파일 적재 이력 — @latest_ym 산출 기준';


-- ============================================================
-- [11] 기업 목록 및 크롤링 설정  (유지보수 핵심 테이블)
--     is_active 토글로 크롤링 대상 제어 — 코드 수정 없이 운영
-- ============================================================
CREATE TABLE IF NOT EXISTS company_config (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    company_name    VARCHAR(100)    NOT NULL COMMENT '기업명 (예: 현대자동차)',
    company_url     VARCHAR(500)    NOT NULL COMMENT 'FAQ 페이지 URL',

    -- 분류
    brand_type      ENUM(
                      '국산', '수입'
                    )               NOT NULL COMMENT '국산/수입 구분',

    -- 연관 키워드 (FAQ 필터링 기준)
    keywords        JSON            NOT NULL COMMENT '연관 키워드 배열 (예: ["전기차","EV","아이오닉"])',

    -- 연관 연료/차종 (트렌드 연계)
    related_fuel    VARCHAR(50)         NULL COMMENT '연관 연료 (예: 전기, 수소)',
    related_car_type VARCHAR(50)        NULL COMMENT '연관 차종 (예: 승용, SUV)',

    -- 크롤링 제어
    is_active       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '크롤링 활성화 (1=활성, 0=비활성)',
    crawl_interval_days TINYINT UNSIGNED NOT NULL DEFAULT 30 COMMENT '크롤링 주기(일)',
    last_crawled_at TIMESTAMP           NULL COMMENT '마지막 크롤링 일시',

    -- 이력
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_company (company_name),
    INDEX idx_is_active   (is_active),
    INDEX idx_brand_type  (brand_type)
) ENGINE=InnoDB COMMENT='기업 FAQ 크롤링 설정 — is_active로 활성화 제어';


-- ============================================================
-- [12] 기업 FAQ 데이터  (크롤링 결과 저장)
-- ============================================================
CREATE TABLE IF NOT EXISTS company_faq (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    company_id      INT UNSIGNED    NOT NULL COMMENT 'company_config.id FK',

    -- FAQ 내용
    question        TEXT            NOT NULL COMMENT '질문',
    answer          MEDIUMTEXT          NULL COMMENT '답변',
    category        VARCHAR(100)        NULL COMMENT 'FAQ 카테고리 (예: 충전, AS, 보증)',

    -- 키워드 추출 (크롤링 후 필터링용)
    extracted_keywords JSON             NULL COMMENT '질문에서 추출된 키워드',

    -- 출처
    source_url      VARCHAR(500)        NULL COMMENT '크롤링 원본 URL',
    crawled_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '크롤링 일시',

    -- 유효 여부 (재크롤링 시 구버전 비활성화)
    is_valid        TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '유효 여부 (1=현행, 0=구버전)',

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_faq_company
        FOREIGN KEY (company_id) REFERENCES company_config (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_company_id (company_id),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_is_valid   (is_valid),
    FULLTEXT INDEX ft_question (question) COMMENT '질문 전문 검색'
) ENGINE=InnoDB COMMENT='기업 FAQ 크롤링 데이터';


-- ============================================================
-- [13] 트렌드 분석 결과 캐시  (Streamlit 조회 성능 최적화)
--      SELECT 쿼리 결과를 저장해두고 재사용
-- ============================================================
CREATE TABLE IF NOT EXISTS trend_analysis_cache (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,

    -- 분석 기준
    analysis_type   VARCHAR(100)    NOT NULL COMMENT '분석 유형 (예: fuel_trend, age_group_trend)',
    base_year_month CHAR(6)             NULL COMMENT '기준 년월',
    period_years    TINYINT UNSIGNED    NULL COMMENT '분석 기간(년)',

    -- 결과
    result_json     JSON            NOT NULL COMMENT '분석 결과 JSON',
    trend_keyword   VARCHAR(100)        NULL COMMENT '도출된 트렌드 키워드 (FAQ 매핑용)',

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP           NULL COMMENT '캐시 만료 일시',

    PRIMARY KEY (id),
    INDEX idx_analysis_type  (analysis_type),
    INDEX idx_trend_keyword  (trend_keyword),
    INDEX idx_expires_at     (expires_at)
) ENGINE=InnoDB COMMENT='트렌드 분석 결과 캐시 — Streamlit 응답속도 개선용';


-- ============================================================
-- 기본 데이터: company_config 초기 기업 등록 예시
-- ============================================================
INSERT INTO company_config
    (company_name, company_url, brand_type, keywords, related_fuel, related_car_type, is_active, crawl_interval_days)
VALUES
    ('현대자동차', 'https://www.hyundai.com/kr/ko/service-center/faq',
     '국산', '["전기차","EV","아이오닉","수소","넥쏘","하이브리드"]', '전기', '승용', 1, 30),

    ('기아', 'https://www.kia.com/kr/customer-service/center/faq',
     '국산', '["전기차","EV6","EV9","하이브리드","스포티지"]', '전기', '승용', 1, 30),

    ('BMW코리아', 'https://www.bmw.co.kr/ko/topics/offers-and-services/service/faq.html',
     '수입', '["전기차","iX","i4","수입차","프리미엄"]', '전기', '승용', 1, 30),

    ('테슬라코리아', 'https://www.tesla.com/ko_kr/support',
     '수입', '["전기차","모델3","모델Y","오토파일럿","충전"]', '전기', '승용', 1, 30),

    ('르노코리아', 'https://www.renaultkorea.com/customer/faq',
     '국산', '["경형","소형","LPG","엘피지"]', '엘피지', '승용', 0, 30),

    ('한국GM', 'https://www.chevrolet.co.kr/customer/faq',
     '국산', '["SUV","트레일블레이저","경형"]', NULL, '승용', 0, 30);

-- ============================================================
-- 확인용 쿼리
-- ============================================================
-- SHOW TABLES;
-- DESC car_yearly_stats;
-- DESC car_fuel_stats;
-- DESC company_config;
-- DESC company_faq;
-- SELECT company_name, is_active, keywords FROM company_config;

-- 기존 DB에 적용할 경우 아래 ALTER 실행 (테이블이 이미 존재할 때)
ALTER TABLE car_fuel_stats
MODIFY COLUMN fuel_type ENUM(
    '휘발유', '경유', '엘피지', '전기', '수소', '수소전기',
    'CNG', 'LNG', '등유', '알코올', '태양열',
    '하이브리드(휘발유+전기)', '하이브리드(경유+전기)',
    '하이브리드(LPG+전기)', '하이브리드(CNG+전기)',
    '하이브리드(LNG+전기)', '기타연료'
) NOT NULL COMMENT '연료 종류';