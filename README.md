# SKN32-1st-1Team
# 🚗 자동차 등록 트렌드 × 기업 FAQ 조회 시스템

안녕하세요!  
이 프로젝트는 단순히 “FAQ를 검색하는 소비자 편의 기능”에서 끝나지 않습니다.  
전국 자동차 등록 현황과 자동차 기업 FAQ 데이터를 함께 보면서,  
**등록 트렌드 변화에 따라 어떤 기업군에서 어떤 고객 문의 이슈가 나타나는지 모니터링하는 데이터 조회 시스템**을 목표로 합니다. ✨

---

## 🎯 프로젝트 핵심 방향

> “FAQ 조회시스템”을 소비자 편의 기능으로만 두지 말고,  
> 자동차 등록 트렌드에 따라 관련 기업군의 고객 문의 이슈를 모니터링하는 자료로 만든다.

즉, 이 프로젝트는 아래 두 데이터를 연결해서 봅니다.

1. **전국 자동차 등록 현황**
   - 연도별 / 월별 등록 추이
   - 지역별 등록 현황
   - 차종, 연료, 용도 등 자동차 시장 변화

2. **자동차 기업 FAQ 데이터**
   - 브랜드별 고객 문의 주제
   - 전기차, 충전, 서비스, 정비, 앱, 보증, 구매, 등록 관련 이슈
   - 기업별 고객 대응 관심사 비교

---

## 🧭 왜 FAQ 데이터를 모으는가?

FAQ는 단순한 “자주 묻는 질문” 목록이 아닙니다.  
기업 입장에서는 고객들이 반복적으로 궁금해하는 지점이 모인 **고객 이슈 데이터**입니다.

예를 들어:

- 전기차 등록이 늘어나면  
  → 충전, 배터리, 주행 가능 거리, 보조금 관련 FAQ가 중요해질 수 있습니다.

- 수입차 등록이 증가하면  
  → 보증, 서비스센터, 부품, 커넥티드 서비스 관련 문의가 중요해질 수 있습니다.

- 특정 지역에서 특정 차종 등록이 늘어나면  
  → 해당 지역의 서비스 수요나 정비 문의 증가를 예측하는 데 참고할 수 있습니다.

그래서 FAQ 데이터는 소비자 검색용을 넘어서,  
**기업 고객 대응 전략과 시장 트렌드 분석에 활용 가능한 자료**가 됩니다. 🔍

---

## 🏢 수집 대상 기업

현재 또는 향후 수집 가능한 자동차 브랜드는 아래와 같습니다.

| 구분 | 브랜드 |
|---|---|
| 국내 완성차 | 현대, 기아, 쉐보레 |
| 수입차 | BMW, Cadillac |
| 추가 가능 | Porsche, Mercedes-Benz, MINI, Lexus 등 |

브랜드는 계속 추가될 수 있습니다.  
중요한 것은 모든 브랜드 데이터를 비슷한 구조로 저장해서, 나중에 통합 조회가 가능하게 만드는 것입니다.

---

## 🗄️ FAQ DB 공통 구조

브랜드별 DB나 테이블 이름은 다를 수 있지만, FAQ 데이터는 아래 구조를 기준으로 맞추는 것을 권장합니다.

```text
faq
├── id
├── brand
├── category
├── question
├── raw_question
├── answer
├── source_url
└── crawled_at
```

### 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `id` | FAQ 고유 번호 |
| `brand` | 브랜드명. 예: BMW, Porsche, Hyundai |
| `category` | FAQ 카테고리. 예: 충전, 서비스, 구매, 앱 |
| `question` | 정제된 질문 |
| `raw_question` | 원본 질문 |
| `answer` | 답변 본문 |
| `source_url` | 크롤링 출처 URL |
| `crawled_at` | 수집 시각 |

현재 일부 팀원 DB에는 `brand` 컬럼이 없을 수 있습니다.  
그 경우 조회 시스템에서 테이블명 또는 DB명으로 브랜드를 구분하거나, 통합 테이블을 만들 때 `brand` 컬럼을 추가하면 됩니다.

---

## 🧩 브랜드별 FAQ 활용 예시

### BMW

- FAQ 수가 많고 주제가 다양합니다.
- 앱, 커넥티드 서비스, 충전, 디지털 키, 서비스 이력 등 디지털/서비스형 문의가 많습니다.
- 수입차 고객지원 이슈를 보기 좋습니다.

### Porsche

- 질문 앞 `[충전]`, `[개인정보보호]`, `[계약]`처럼 카테고리가 명확합니다.
- 전기차 충전, 커넥트 서비스, 인증 중고차, 긴급출동 등 기업 대응 이슈가 잘 드러납니다.

### 현대 / 기아 / 쉐보레 / 캐딜락

- 국내외 브랜드 비교용으로 활용할 수 있습니다.
- 구매, 정비, 보증, 부품, 서비스센터, 전기차 관련 문의 흐름을 비교하기 좋습니다.

---

## 📊 자동차 등록 현황과 FAQ를 연결하는 방법

이 프로젝트의 재미는 여기서 시작됩니다. 🌈

FAQ만 보면 “고객 질문 목록”이지만,  
등록 현황과 함께 보면 “시장 변화에 따른 고객 이슈”가 됩니다.

예시 분석 방향:

```text
전기차 등록 증가
→ 충전 / 배터리 / 주행 가능 거리 FAQ 증가 여부 확인

수입차 등록 증가
→ 서비스센터 / 보증 / 부품 / 커넥티드 서비스 FAQ 비교

지역별 등록 차이
→ 지역 기반 서비스 수요나 고객지원 이슈 해석

월별 신규 등록 변화
→ 구매 / 계약 / 인도 / 보조금 문의 주제와 연결
```

---

## 🔎 추천 조회 쿼리

### 브랜드별 FAQ 건수

```sql
SELECT brand, COUNT(*) AS faq_count
FROM faq
GROUP BY brand
ORDER BY faq_count DESC;
```

### 브랜드별 카테고리 분포

```sql
SELECT brand, category, COUNT(*) AS cnt
FROM faq
GROUP BY brand, category
ORDER BY brand, cnt DESC;
```

### 전기차/충전 관련 FAQ 검색

```sql
SELECT brand, category, question, answer
FROM faq
WHERE question LIKE '%충전%'
   OR answer LIKE '%충전%'
   OR question LIKE '%배터리%'
   OR answer LIKE '%배터리%';
```

### 서비스/정비 관련 FAQ 검색

```sql
SELECT brand, category, question, answer
FROM faq
WHERE question LIKE '%서비스%'
   OR answer LIKE '%서비스%'
   OR question LIKE '%정비%'
   OR answer LIKE '%정비%'
   OR question LIKE '%보증%'
   OR answer LIKE '%보증%';
```

---

## 🖥️ Streamlit 조회 시스템 방향

Streamlit 화면은 크게 두 영역으로 나눌 수 있습니다.

### 1. 전국 자동차 등록 현황

- 연도별 등록 추이
- 월별 등록 추이
- 지역별 등록 현황
- 연료별 / 차종별 / 용도별 등록 현황

### 2. 기업 FAQ 조회

- 브랜드별 FAQ 검색
- 카테고리별 FAQ 필터
- 전기차/충전/서비스/구매 등 이슈 키워드 검색
- 브랜드별 FAQ 주제 비교

핵심은 두 데이터를 따로 보여주는 것이 아니라,  
**등록 트렌드 변화와 FAQ 이슈를 함께 해석할 수 있게 만드는 것**입니다.

---

## 📁 현재 별도 정리된 크롤링 폴더 예시

```text
bmw_faq_project/
├── bmw_faq_crawler.py
├── bmw_faq_schema.sql
└── README.md

porsche_faq_project/
├── porsche_faq_crawler.py
├── porsche_faq_schema.sql
└── README.md
```

다른 브랜드도 같은 방식으로 정리하면 좋습니다.

```text
brand_faq_project/
├── brand_faq_crawler.py
├── brand_faq_schema.sql
└── README.md
```

---

## ✅ 데이터 품질 체크 포인트

크롤링 후에는 아래 항목을 꼭 확인합니다.

- 질문이 누락되지 않았는가?
- 답변이 미리보기 문장만 저장되지 않았는가?
- 빈 답변이 있는가?
- 카테고리가 제대로 들어갔는가?
- 출처 URL이 저장되었는가?
- 중복 질문이 있는가?

예시 쿼리:

```sql
SELECT COUNT(*) AS total_count
FROM faq;

SELECT COUNT(*) AS empty_answer_count
FROM faq
WHERE answer IS NULL
   OR TRIM(answer) = '';

SELECT category, COUNT(*) AS cnt
FROM faq
GROUP BY category
ORDER BY cnt DESC;
```

---

## 💬 한 줄 요약

이 프로젝트는 자동차 FAQ를 그냥 모아두는 것이 아니라,  
**자동차 등록 트렌드와 고객 문의 이슈를 함께 읽는 기업형 데이터 조회 시스템**입니다. 🚙📈

고객이 무엇을 궁금해하는지, 시장이 어디로 움직이는지,  
그 둘을 같이 보는 것이 이 프로젝트의 핵심입니다. ✨
