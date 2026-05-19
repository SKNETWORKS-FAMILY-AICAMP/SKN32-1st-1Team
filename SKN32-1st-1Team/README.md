# 전국 자동차 등록 현황 및 기업 FAQ 조회 시스템

> 국토교통부 자동차 등록 데이터를 시계열로 분석하고,  
> 트렌드와 연동된 기업 FAQ를 함께 조회할 수 있는 통합 대시보드

**Team** : 소나기 1팀 | SKN Family AI Camp 32기 1차 프로젝트
| 역할 | 이름 |
| --- |   --- |
| 팀장 | 오한빈 |
| 팀원 | 김택현 |
| 팀원 | 신지은 |
| 팀원 | 최상욱 |
| 팀원 | 하정원 |
---

## 목차

1. [프로젝트 소개](#1-프로젝트-소개)
2. [주제 선정 이유](#2-주제-선정-이유)
3. [주요 기능](#3-주요-기능)
4. [시스템 구조](#4-시스템-구조)
5. [기술 스택](#5-기술-스택)
6. [데이터 소스](#6-데이터-소스)
7. [설치 및 실행](#7-설치-및-실행)
8. [DB 구조](#8-db-구조)
9. [크롤러 관리](#9-크롤러-관리)
10. [팀 정보](#10-팀-정보)

---

## 1. 프로젝트 소개

국토교통부가 매월 공개하는 **전국 자동차 등록 현황** 데이터를 DB에 적재하고,  
연료·차종·지역·연령 등 다양한 기준으로 트렌드를 분석합니다.  
분석된 트렌드 키워드는 **기업 FAQ 검색과 자동 연동**되어,  
"어떤 차가 뜨고 있는지"와 "고객이 무엇을 궁금해하는지"를 한 화면에서 확인할 수 있습니다.
사용자는 전국 자동차 등록 현황의 세부 항목 통계들을 쉽게 표와 시각차트로 조회할 수 있습니다. 
---

## 2. 주제 선정 이유

### 데이터 관점

| 데이터 | 특성 | 활용 목적 |
|---|---|---|
| 전국 자동차 등록 현황 | 년·월별 정량 수치 (차종·연료·지역·연령 등) | 시간 흐름에 따른 트렌드 및 증감 파악 |
| 기업 FAQ | 고객이 가장 많이 묻는 Q&A 텍스트 | 트렌드 차종에 대한 실제 고객 관심사 확인 |

두 데이터를 결합하면 **"통계로 확인된 트렌드"** 와 **"현장 고객의 목소리"** 를 동시에 파악할 수 있습니다.

### 프로젝트 전략

- 크롤링 성능보다 **데이터 신뢰도·정확성** 에 집중
- 등록 현황 데이터를 충분히 분석한 뒤, 트렌드에 맞는 기업 FAQ를 선별하여 연동
- 코드 기능(DB Select)으로 트렌드를 산출하고, `company_config` 테이블의 `is_active` 컬럼으로 기업별 크롤링을 on/off 제어 → 트렌드가 바뀌어도 유지보수 비용 최소화

---

## 3. 주요 기능

### 트렌드 대시보드
- 연료별 단기 트렌드 (최근 6개월 vs 이전 6개월 평균 비교)
- 승용 차종별 트렌드
- 배기량 구간별 트렌드
- 성별·연령대별 등록 트렌드
- 수입차 비중 월별 추이 (라인 차트 + 전월 대비)
- 연도별 시장 규모·성장률·차종별 현황·지역별 증감

### FAQ 검색
- 트렌드 대시보드의 **급증 연료 Top 3** 가 FAQ 키워드로 자동 전달
- 브랜드 필터 (전체 선택/개별 선택)
- 직접 검색어 입력
- 페이지네이션 (10건씩, 5페이지 단위 그룹)

### 통계 분석
- 연식별 차량 대수 조회
- 연료/배기량별 차량 등록 수 추이
- 성별·연령별 등록 추이
- 연간 자동차 등록 추이
- 지역별 등록 증감 순위

---

## 4. 시스템 구조

```
SKN32-1st-1Team/
├── modules/
│   ├── connect_db.py           # DB 연결 공통 유틸
│   ├── trend_dashboard.py      # 트렌드 대시보드 페이지
│   ├── faq_search.py           # FAQ 검색 페이지
│   └── stats_dashboard.py      # 통계 분석 페이지
│
├── crawler/
│   ├── hyundai_faq_crawler.py
│   ├── kia_faq_crawler.py
│   ├── bmw_faq_crawler.py
│   ├── genesis_faq_crawler.py
│   ├── cadillac_faq_crawler.py
│   ├── chevrolet_faq_crawler.py
│   ├── porsche_faq_crawler.py
│   ├── volkswagen_faq_crawler.py
│   └── main.py                 # 전체 크롤러 통합 실행
│
├── data/
|   ├──auto_data/               # 국토교통부 엑셀 통계 데이터 저장폴더
│   ├── data_downloader.py      # 국토교통부 엑셀 자동 다운로드
│   └── load_to_db.py           # 엑셀 → DB 적재
│
├── sql/
│   ├── ddl/
│   │   └── car_registration_db.sql     # 테이블 스키마 정의
│   └── query/
│       └── trend_analysis_queries.sql  # 트렌드 분석 쿼리 모음
│
├── app.py                      # Streamlit 통합 진입점
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 5. 기술 스택

| 분류 | 기술 |
|---|---|
| 언어 | Python 3.x |
| 대시보드 | Streamlit 1.57.0 |
| 데이터 처리 | Pandas 2.2, Plotly 5.24 |
| DB | MySQL 8.0 |
| DB 연결 | PyMySQL 1.1, SQLAlchemy 2.0, mysql-connector-python 9.7 |
| 크롤링 | Selenium 4.27, Playwright 1.59, BeautifulSoup4 4.12 |
| 드라이버 관리 | webdriver-manager 4.0 |
| 엑셀 파싱 | openpyxl 3.1 |
| 환경변수 | python-dotenv 1.2 |

---

## 6. 데이터 소스

### 전국 자동차 등록 현황
- **출처** : 국토교통부 공공데이터포털 (월별 엑셀 파일)
- **링크** : https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58
- **갱신 주기** : 매월
- **주요 항목** : 차종·연료·지역·용도·성별·연령대·배기량·국산/수입 구분

### 기업 FAQ
- **출처** : 각 브랜드 공식 홈페이지 FAQ 페이지
- **갱신 주기** : 1개월 ~ 6개월
- **수집 대상** : 현대·기아·제네시스·BMW·포르쉐·캐딜락·쉐보레·폭스바겐
- 기아 FAQ - https://www.kia.com/kr/customer-service/center/faq
- bmw FAQ - https://www.bmw.co.kr/kr/s/?language=ko
- 포르쉐 FAQ - https://www.porsche.com/korea/ko/faq/
- 폭스바겐 FAQ - https://www.volkswagen.co.kr/ko/faq.html
- 쉐보레 FAQ - https://www.chevrolet.co.kr/faq
- 현대자동차 FAQ - https://www.hyundai.com/kr/ko/faq.html
- 제네시스 FAQ - https://www.genesis.com/kr/ko/support/faq.html
- 케딜락 FAQ - https://www.cadillac.co.kr/onstar/onstar-faq
---

## 7. 설치 및 실행

### 가상환경 vscode cmd 터미널 설치
- python -m venv .venv (설치) → .venv\Scripts\activate (실행)


### 사전 요구사항
- Python 3.10 이상
- MySQL 8.0 이상
- Google Chrome (Selenium 크롤러용)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/SKN32-1st-1Team/프로젝트명.git
cd SKN32-1st-1Team

# 2. 패키지 설치
pip install -r requirements.txt

# 3. Playwright 브라우저 설치 (기아·폭스바겐 크롤러용)
playwright install chromium
```

### 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성합니다.

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=sknmainproject1_db
```
### 실행 순서

- sql/ddl/car_registration_db.sql - DB 구축
- car_registration_downloader.py - 전국 자동차 등록현황 엑셀 데이터파일 다운로드
- load_to_db.py - DB에 데이터 적재
- crawler/main.py - 크롤링 후 DB 에 데이터 적재

### DB 초기화

```bash
mysql -u root -p < sql/ddl/car_registration_db.sql
```

### 데이터 적재

```bash
# 엑셀 파일을 data/ 폴더에 준비한 뒤 실행
python data/load_to_db.py
```

### FAQ 크롤링 (선택)

```bash
cd crawler
python main.py
```

### 대시보드 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 8. DB 구조

주요 테이블 목록:

| 테이블 | 설명 |
|---|---|
| `car_fuel_stats` | 연료별 월간 등록 현황 |
| `car_type_detail_stats` | 차종별 세부 월간 등록 현황 |
| `car_displacement_stats` | 배기량별 월간 등록 현황 |
| `car_gender_age_stats` | 성별·연령대별 월간 등록 현황 |
| `car_region_stats` | 지역별 월간 등록 현황 |
| `car_yearly_stats` | 차종별 연간 등록 현황 |
| `car_new_registration` | 신조차·수입차·부활차 월간 현황 |
| `car_age_stats` | 연식별 등록 현황 |
| `load_history` | 데이터 적재 이력 |
| `company_config` | 크롤링 대상 기업 설정 |
| `company_faq` | 수집된 기업 FAQ 데이터 |

ERD 시각화: 프로젝트 루트의 `erd.html` 파일을 브라우저에서 열어 확인

---

## 9. 크롤러 관리

트렌드가 변화하더라도 코드 수정 없이 DB에서 크롤링 대상을 제어할 수 있습니다.

### 특정 기업 비활성화

```sql
UPDATE company_config SET is_active = 0 WHERE company_name = '폭스바겐';
```

### 새 기업 추가

```sql
INSERT INTO company_config (company_name, company_url, brand_type, keywords, is_active)
VALUES ('토요타', 'https://toyota.co.kr/...', '수입', '["하이브리드","SUV"]', 1);
```

새 기업 크롤러 파일(`crawler/toyota_faq_crawler.py`)을 작성하고 `crawler/main.py`에 등록하면 됩니다.

---

## 10. 팀 정보

**소나기 1팀** | SKN Family AI Camp 32기 1차 프로젝트

| 역할 | 이름 |
| --- |   --- |
| 팀장 | 오한빈 |
| 팀원 | 김택현 |
| 팀원 | 신지은 |
| 팀원 | 최상욱 |
| 팀원 | 하정원 |
