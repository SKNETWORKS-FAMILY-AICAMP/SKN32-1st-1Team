-- ============================================================
--  전국 자동차 등록 현황 트렌드 분석 쿼리 모음
--  소나기 팀 | 2026
--
--  [수정 이력]
--  v2 - 오류 수정 (콜레이션·UNSIGNED·LAG·SUV비중·is_last)
--  v3 - 고정 카테고리 필터 전면 제거, 롱 포맷 전환
--  v4 - 주제별 재구성, 중복 제거, 섹션명 중립화
--
--  [섹션 구조]
--  [연료별 트렌드]   M-1 M-2 Y-1 Y-2
--  [차종·배기량]     M-3 M-4 Y-3 Y-4
--  [구매층 트렌드]   M-5 M-6
--  [지역별 트렌드]   M-7
--  [신규등록·수입]   Y-5
--  [FAQ 연계]
--  [유지보수]
--
--  [핵심 설계 원칙]
--  - @latest_ym 자동 기준 → 새 파일 적재 시 자동 반영
--  - 카테고리 IN 필터 없음 → 데이터 변동 시 순위 자동 변경
--  - 최근3개월 vs 이전3개월 트렌드 방향 자동 감지 (UP/DOWN/FLAT)
--  - M- (월별 시각화용) / Y- (연도별 장기 분석용)
-- ============================================================


-- ============================================================
-- [공통] 세션 초기화 — Python 에서 먼저 실행
-- ============================================================
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET SESSION sql_mode = CONCAT(@@sql_mode, ',NO_UNSIGNED_SUBTRACTION');

SET @latest_ym = (SELECT MAX(year_months) FROM load_history);
SET @start_ym  = (SELECT MIN(year_months) FROM load_history);
SET @period    = 12;  -- Streamlit 슬라이더 연동 (6 / 12 / 24)

SET @period_start_ym = DATE_FORMAT(
    DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),
             INTERVAL @period MONTH),
    '%Y%m');


-- ============================================================
-- [공통] 대시보드 요약 카드
-- ============================================================
SELECT
    (SELECT MAX(year_months) FROM load_history)            AS latest_ym,
    (SELECT MIN(year_months) FROM load_history)            AS oldest_ym,
    (SELECT COUNT(DISTINCT year_months) FROM load_history) AS total_months,

    (SELECT cnt_total FROM car_region_stats
     WHERE year_months = @latest_ym
       AND region = '합계' AND car_type = '합계')         AS total_registered,

    (SELECT registered_count FROM car_fuel_stats
     WHERE year_months = @latest_ym AND fuel_type = '전기'
       AND car_type = '소계' AND usage_type = '계'
       AND region = '합계')                               AS ev_total,

    (SELECT SUM(registered_count) FROM car_fuel_stats
     WHERE year_months = @latest_ym
       AND fuel_type LIKE '하이브리드%'
       AND car_type = '소계' AND usage_type = '계'
       AND region = '합계')                               AS hybrid_total,

    (SELECT registered_count FROM car_type_detail_stats
     WHERE year_months = @latest_ym AND car_type = '승용'
       AND car_subtype = '다목적' AND region = '합계')    AS suv_total;


-- ============================================================
-- [연료별 트렌드]
--   M-1: 월별 시계열 (시각화용 롱 포맷)
--   M-2: 단기 트렌드 방향 (최근3개월 vs 이전3개월)
--   Y-1: 연간 스냅샷 (연도별 YoY)
--   Y-2: 장기 성장 순위 (최근12개월 vs 이전12개월)
-- ============================================================

-- M-1. 연료별 월별 등록 추이 (전체 연료, 롱 포맷)
--      Streamlit 에서 top-N 또는 특정 연료 필터링
SELECT
    year_months,
    fuel_type,
    registered_count,
    registered_count
        - LAG(registered_count)
          OVER (PARTITION BY fuel_type ORDER BY year_months) AS mom_diff,
    ROUND(
        (registered_count
         - LAG(registered_count)
           OVER (PARTITION BY fuel_type ORDER BY year_months))
        / NULLIF(LAG(registered_count)
           OVER (PARTITION BY fuel_type ORDER BY year_months), 0) * 100
    , 2)                                                      AS mom_rate
FROM car_fuel_stats
WHERE year_months BETWEEN @period_start_ym AND @latest_ym
  AND car_type = '소계' AND usage_type = '계' AND region = '합계'
ORDER BY fuel_type, year_months;


-- M-2. 연료별 단기 트렌드 방향 자동 감지 (최근3개월 vs 이전3개월)
WITH fuel_ranked AS (
    SELECT year_months, fuel_type, registered_count,
        ROW_NUMBER() OVER (PARTITION BY fuel_type ORDER BY year_months DESC) AS rn
    FROM car_fuel_stats
    WHERE car_type = '소계' AND usage_type = '계' AND region = '합계'
),
recent3 AS (
    SELECT fuel_type, AVG(registered_count) AS avg_r
    FROM fuel_ranked WHERE rn <= 3 GROUP BY fuel_type
),
prev3 AS (
    SELECT fuel_type, AVG(registered_count) AS avg_p
    FROM fuel_ranked WHERE rn BETWEEN 4 AND 6 GROUP BY fuel_type
)
SELECT
    r.fuel_type,
    ROUND(r.avg_r)                                    AS recent_3m_avg,
    ROUND(p.avg_p)                                    AS prev_3m_avg,
    ROUND(r.avg_r - p.avg_p)                          AS abs_diff,
    ROUND((r.avg_r - p.avg_p) / NULLIF(p.avg_p,0) * 100, 2) AS change_pct,
    CASE
        WHEN (r.avg_r - p.avg_p) / NULLIF(p.avg_p,0) >  0.005 THEN 'UP'
        WHEN (r.avg_r - p.avg_p) / NULLIF(p.avg_p,0) < -0.005 THEN 'DOWN'
        ELSE 'FLAT'
    END                                               AS trend_direction
FROM recent3 r
JOIN prev3   p ON r.fuel_type = p.fuel_type
ORDER BY change_pct DESC;


-- Y-1. 연료별 연간 스냅샷 (각 연도 12월 기준, 미완료 연도는 최신월)
SELECT
    YEAR(STR_TO_DATE(CONCAT(year_months,'01'),'%Y%m%d')) AS stat_year,
    CASE
        WHEN year_months = @latest_ym AND RIGHT(year_months,2) != '12'
        THEN CONCAT(RIGHT(year_months,2),'월 기준(진행중)')
        ELSE '12월 기준'
    END                                                  AS note,
    fuel_type,
    registered_count,
    registered_count
        - LAG(registered_count)
          OVER (PARTITION BY fuel_type ORDER BY year_months) AS yoy_diff,
    ROUND(
        (registered_count
         - LAG(registered_count)
           OVER (PARTITION BY fuel_type ORDER BY year_months))
        / NULLIF(LAG(registered_count)
           OVER (PARTITION BY fuel_type ORDER BY year_months), 0) * 100
    , 2)                                                 AS yoy_rate
FROM car_fuel_stats
WHERE year_months IN (
      SELECT COALESCE(
          MAX(CASE WHEN RIGHT(year_months,2)='12' THEN year_months END),
          MAX(year_months)
      )
      FROM car_fuel_stats
      WHERE car_type = '소계' AND usage_type = '계' AND region = '합계'
      GROUP BY LEFT(year_months,4)
  )
  AND car_type = '소계' AND usage_type = '계' AND region = '합계'
ORDER BY fuel_type, year_months;


-- Y-2. 연료별 장기 성장 순위 (최근12개월 vs 이전12개월 합계 비교)
WITH fuel_period AS (
    SELECT
        fuel_type,
        SUM(CASE
            WHEN year_months > DATE_FORMAT(
                    DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),
                             INTERVAL 12 MONTH), '%Y%m')
             AND year_months <= @latest_ym
            THEN registered_count END)                    AS recent_12m,
        SUM(CASE
            WHEN year_months > DATE_FORMAT(
                    DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),
                             INTERVAL 24 MONTH), '%Y%m')
             AND year_months <= DATE_FORMAT(
                    DATE_SUB(STR_TO_DATE(CONCAT(@latest_ym,'01'),'%Y%m%d'),
                             INTERVAL 12 MONTH), '%Y%m')
            THEN registered_count END)                    AS prev_12m
    FROM car_fuel_stats
    WHERE car_type = '소계' AND usage_type = '계' AND region = '합계'
    GROUP BY fuel_type
)
SELECT
    fuel_type,
    recent_12m,
    prev_12m,
    recent_12m - prev_12m                                AS diff,
    ROUND((recent_12m - prev_12m) / NULLIF(prev_12m,0) * 100, 2) AS yoy_rate,
    CASE
        WHEN recent_12m > prev_12m * 1.05 THEN 'UP'
        WHEN recent_12m < prev_12m * 0.95 THEN 'DOWN'
        ELSE 'FLAT'
    END                                                  AS trend_direction
FROM fuel_period
WHERE prev_12m > 0
ORDER BY yoy_rate DESC;


-- ============================================================
-- [차종·배기량 트렌드]
--   M-3: 승용 차종별(SUV/일반 등) 월별 비중
--   M-4: 배기량별 월별 추이
--   Y-3: 차종별 연도별 증감
--   Y-4: 전체 시장 연도별 증감
-- ============================================================

-- M-3. 승용 차종별 월별 비중 (전체 차종 자동 반환)
SELECT
    year_months,
    car_subtype,
    registered_count,
    ROUND(
        registered_count
        / NULLIF(MAX(CASE WHEN car_subtype = '계'
                          THEN registered_count END)
                 OVER (PARTITION BY year_months), 0) * 100
    , 2)                                                  AS share_pct
FROM car_type_detail_stats
WHERE year_months BETWEEN @period_start_ym AND @latest_ym
  AND car_type = '승용' AND region = '합계'
ORDER BY year_months, car_subtype;


-- M-4. 배기량별 월별 추이
SELECT
    year_months,
    displacement,
    registered_count,
    registered_count
        - LAG(registered_count)
          OVER (PARTITION BY displacement ORDER BY year_months) AS mom_diff,
    CASE
        WHEN registered_count > LAG(registered_count)
             OVER (PARTITION BY displacement ORDER BY year_months) THEN 'UP'
        WHEN registered_count < LAG(registered_count)
             OVER (PARTITION BY displacement ORDER BY year_months) THEN 'DOWN'
        ELSE 'FLAT'
    END                                                        AS trend_direction
FROM car_displacement_stats
WHERE year_months BETWEEN @period_start_ym AND @latest_ym
  AND region = '합계'
ORDER BY displacement, year_months;


-- Y-3. 차종별 연도별 증감 (완전한 연도만)
SELECT
    stat_year,
    car_type,
    registered_count,
    registered_count
        - LAG(registered_count)
          OVER (PARTITION BY car_type ORDER BY stat_year) AS yoy_diff,
    ROUND(
        (registered_count
         - LAG(registered_count)
           OVER (PARTITION BY car_type ORDER BY stat_year))
        / NULLIF(LAG(registered_count)
           OVER (PARTITION BY car_type ORDER BY stat_year), 0) * 100
    , 2)                                                   AS yoy_rate
FROM car_yearly_stats
WHERE usage_type = '합계'
  AND stat_year  < YEAR(CURDATE())
ORDER BY car_type, stat_year;


-- Y-4. 전체 시장 연도별 증감 (완전한 연도만)
SELECT
    stat_year,
    registered_count,
    registered_count
        - LAG(registered_count) OVER (ORDER BY stat_year) AS yoy_diff,
    ROUND(
        (registered_count
         - LAG(registered_count) OVER (ORDER BY stat_year))
        / NULLIF(LAG(registered_count) OVER (ORDER BY stat_year), 0) * 100
    , 2)                                                   AS yoy_rate
FROM car_yearly_stats
WHERE car_type   = '합계'
  AND usage_type = '합계'
  AND stat_year  < YEAR(CURDATE())
ORDER BY stat_year;


-- ============================================================
-- [구매층 트렌드]
--   M-5: 성별·연령대별 월별 추이
--   M-6: 성별·연령대 트렌드 방향 (3개월 rolling)
-- ============================================================

-- M-5. 성별·연령대별 월별 추이 (법인·사업자 제외)
SELECT
    year_months,
    gender,
    age_group,
    registered_count,
    registered_count
        - LAG(registered_count)
          OVER (PARTITION BY gender, age_group ORDER BY year_months) AS mom_diff,
    CASE
        WHEN age_group IN ('20대','30대','40대','50대') THEN '핵심구매층'
        ELSE '참고'
    END                                                              AS segment
FROM car_gender_age_stats
WHERE year_months BETWEEN @period_start_ym AND @latest_ym
  AND region    = '합계'
  AND gender   IN ('남성', '여성')
  AND age_group IN ('20대','30대','40대','50대',
                    '60대','70대','80대','90대이상')
ORDER BY
    FIELD(age_group,'20대','30대','40대','50대',
                    '60대','70대','80대','90대이상'),
    gender, year_months;


-- M-6. 성별·연령대 트렌드 방향 감지 (절대증감 기준 정렬)
WITH ga_ranked AS (
    SELECT year_months, gender, age_group, registered_count,
        ROW_NUMBER() OVER (PARTITION BY gender, age_group
                           ORDER BY year_months DESC) AS rn
    FROM car_gender_age_stats
    WHERE region  = '합계'
      AND gender IN ('남성', '여성')
      AND age_group IN ('20대','30대','40대','50대',
                        '60대','70대','80대','90대이상')
)
SELECT
    CASE
        WHEN age_group IN ('20대','30대','40대','50대') THEN '핵심구매층'
        ELSE '참고'
    END                                                              AS segment,
    gender,
    age_group,
    ROUND(AVG(CASE WHEN rn <= 3            THEN registered_count END)) AS recent_3m_avg,
    ROUND(AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END)) AS prev_3m_avg,
    ROUND(AVG(CASE WHEN rn <= 3            THEN registered_count END))
        - ROUND(AVG(CASE WHEN rn BETWEEN 4 AND 6
                         THEN registered_count END))                   AS abs_diff,
    ROUND(
        (AVG(CASE WHEN rn <= 3 THEN registered_count END)
         - AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END))
        / NULLIF(AVG(CASE WHEN rn BETWEEN 4 AND 6
                          THEN registered_count END), 0) * 100
    , 2)                                                               AS change_pct,
    CASE
        WHEN AVG(CASE WHEN rn <= 3 THEN registered_count END)
           > AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END) * 1.005
        THEN 'UP'
        WHEN AVG(CASE WHEN rn <= 3 THEN registered_count END)
           < AVG(CASE WHEN rn BETWEEN 4 AND 6 THEN registered_count END) * 0.995
        THEN 'DOWN'
        ELSE 'FLAT'
    END                                                                AS trend_direction
FROM ga_ranked
GROUP BY segment, gender, age_group
ORDER BY FIELD(segment,'핵심구매층','참고'), abs_diff;


-- ============================================================
-- [지역별 트렌드]
--   M-7: 지역별 등록 증감 순위 (@start_ym → @latest_ym)
-- ============================================================

-- M-7. 지역별 등록 증감 순위 (growth_pct 기준 자동 정렬)
WITH reg_latest AS (
    SELECT region, cnt_total FROM car_region_stats
    WHERE year_months = @latest_ym AND car_type = '합계'
),
reg_base AS (
    SELECT region, cnt_total FROM car_region_stats
    WHERE year_months = @start_ym AND car_type = '합계'
)
SELECT
    l.region,
    b.cnt_total                                                 AS base_cnt,
    l.cnt_total                                                 AS latest_cnt,
    l.cnt_total - b.cnt_total                                   AS diff,
    ROUND((l.cnt_total - b.cnt_total) / NULLIF(b.cnt_total,0) * 100, 2) AS growth_pct,
    CASE
        WHEN (l.cnt_total - b.cnt_total) / NULLIF(b.cnt_total,0) >  0.03 THEN 'UP'
        WHEN (l.cnt_total - b.cnt_total) / NULLIF(b.cnt_total,0) < -0.01 THEN 'DOWN'
        ELSE 'FLAT'
    END                                                         AS trend_direction
FROM reg_latest l
JOIN reg_base   b ON l.region = b.region
WHERE l.region != '합계'
ORDER BY growth_pct DESC;


-- ============================================================
-- [신규등록·수입]
--   Y-5: 수입차 비중 월별 추이
-- ============================================================

-- Y-5. 수입차 비중 월별 추이 (신조차+수입차+부활차=합계 검증 포함)
SELECT
    year_months,
    SUM(CASE WHEN reg_type = '신조차' THEN registered_count END) AS sinjo,
    SUM(CASE WHEN reg_type = '수입차' THEN registered_count END) AS import_cnt,
    SUM(CASE WHEN reg_type = '부활차' THEN registered_count END) AS buhwal,
    SUM(CASE WHEN reg_type = '계'     THEN registered_count END) AS total_cnt,
    ROUND(
        SUM(CASE WHEN reg_type = '수입차' THEN registered_count END)
        / NULLIF(SUM(CASE WHEN reg_type = '계'
                          THEN registered_count END), 0) * 100
    , 2)                                                          AS import_pct
FROM car_new_registration
WHERE region   = '합계'
  AND car_type = '합계'
GROUP BY year_months
ORDER BY year_months;


-- ============================================================
-- [FAQ 연계] 트렌드 키워드 × 기업 FAQ 매핑
-- SET @faq_keyword = '전기차';  -- Streamlit 검색창 입력값
-- ============================================================
SELECT
    c.company_name,
    c.brand_type,
    c.related_fuel,
    f.category,
    f.question,
    f.answer,
    f.crawled_at
FROM company_faq   f
JOIN company_config c ON f.company_id = c.id
WHERE c.is_active = 1
  AND f.is_valid  = 1
  AND (
       f.question LIKE CONCAT('%', @faq_keyword, '%')
    OR JSON_CONTAINS(f.extracted_keywords, CONCAT('"', @faq_keyword, '"'))
  )
ORDER BY c.company_name, f.crawled_at DESC;


-- ============================================================
-- [유지보수] 적재 이력 및 기업 활성화 현황
-- ============================================================
SELECT year_months, filename, loaded_at, row_count
FROM load_history
ORDER BY year_months DESC;

SELECT company_name, brand_type, related_fuel, is_active,
       crawl_interval_days, last_crawled_at
FROM company_config
ORDER BY is_active DESC, last_crawled_at DESC;
