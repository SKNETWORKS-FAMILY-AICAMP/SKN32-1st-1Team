import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By

# 1. 파일이 저장될 폴더 설정
download_dir = os.path.abspath("./auto_data")
if not os.path.exists(download_dir):
    os.makedirs(download_dir)
    print(f"'{download_dir}' 폴더를 생성했습니다.")

# 2. 크롬 브라우저 다운로드 및 보안 옵션 설정
chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "profile.default_content_setting_values.multiple_automating_downloads": 1 
}
chrome_options.add_experimental_option("prefs", prefs)

# 3. 브라우저 실행 및 이동
driver = webdriver.Chrome(options=chrome_options)
url = "https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=58"
driver.get(url)
time.sleep(3)

# 4. 모든 링크 태그 수집
links = driver.find_elements(By.TAG_NAME, "a")
download_count = 0

print("[2024년 1월 ~ 2026년 4월] 자동차 등록자료 강제 다운로드 시작...")

for link in links:
    try:
        # 줄바꿈(\n)과 공백을 한 줄로 정제
        text = " ".join(link.text.split())
        
        if "자동차 등록자료" in text:
            match = re.search(r"(\d{4})년\s*(\d{1,2})월", text)
            
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                
                # 타겟 기간 검증 (2024년 1월 ~ 2026년 4월)
                is_target = False
                if year == 2024 or year == 2025:
                    is_target = True
                elif year == 2026 and month <= 4:
                    is_target = True
                
                if is_target:
                    print(f"조건 일치 (강제 다운로드): {year}년 {month}월 파일")
                    
                    # 핵심 수정: 일반 click() 대신 자바스크립트로 강제 클릭 실행
                    driver.execute_script("arguments[0].click();", link)
                    
                    download_count += 1
                    time.sleep(3)  # 다운로드 안정성을 위해 3초 대기

    except Exception as e:
        continue

# 5. 모든 파일이 안전하게 저장될 때까지 대기
print("모든 파일의 다운로드 완료를 위해 잠시 대기합니다...")
time.sleep(12)

print("-" * 50)
print(f"작업이 성공적으로 완료되었습니다!")
print(f"저장 폴더: {download_dir}")
print(f"총 다운로드된 파일 수: {download_count}개")
print("-" * 50)

driver.quit()