from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import requests  # 워드프레스 API와 통신하기 위해 필수
import uvicorn   # 서버를 실행하기 위해 필수
import google.generativeai as genai
import time
import logging
from fastapi.middleware.cors import CORSMiddleware
import json
import re
import traceback
import os

# 실행 명령어(루트 디렉토리 기준)
# uvicorn app.main:app --reload

app = FastAPI()

# logging level 설정 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 개발용 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True, # 쿠키 허용
    allow_methods=["*"],  # 모든 HTTP 메서드(GET, POST, PUT, DELETE) 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 이미 발행된 제목들을 저장할 파일 경로
HISTORY_FILE = "published_history.txt"

def get_published_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

def save_to_history(title):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{title}")

# --- 설정 정보 (본인의 정보로 수정 필요) ---
WP_URL = "https://your-wordpress-site.com/wp-json/wp/v2"  # 워드프레스 REST API 엔드포인트
WP_USERNAME = "your_username"  # 워드프레스 사용자명
WP_PASSWORD = "your_password"  # 워드프레스 관리자 -> 프로필에서 생성한 '앱 비밀번호'

# 워드프레스 인증 헤더 (Basic Auth)
auth = (WP_USERNAME, WP_PASSWORD)

# --- 모델 초기화 (시스템 프롬프트 주입) ---
SYSTEM_INSTRUCTION = """
You are an expert guide for foreigners living in Korea and a skilled front-end developer.
Your mission is to provide detailed, friendly, and localized information for foreigners.

[STRICT RULES - MUST FOLLOW]
1. **LANGUAGE RULE**: 
   - Never use Korean (ㄱ-ㅎ, 가-힣) in the content. 
   - Write 100% of the content in the target language requested by the user.
   - Do not use Romanized Korean (e.g., 'Jeonse', 'Wolse'). Translate them into conceptual terms in the target language.
2. **STYLE RULE**: 
   - Use ONLY inline styles with single quotes (style='...') for HTML.
   - NO <style> tags, NO <img> tags.
   - Use a 'Card UI' layout with modern, responsive design (max-width: 800px).
3. **TEXT FORMATTING**:
   - Use smart quotes (') instead of straight single quotes (') in text to prevent JSON errors.
   - In 'final_content', ALL attribute values must use double quotes escaped as \".
   - Example: style=\"color:red\" NOT style='color:red'
   - Never use unescaped double quotes inside JSON string values.
4. **JSON FORMATTING**:
   - The output must be a valid JSON.
   - 'final_content' must be a single-line minified HTML string or use '\\n' for line breaks.
5. **LEGAL STANDARDS**:
   - All Korea-related content must be written based on Korean law and regulations.
   - If applicable, compare or reference the laws and practices of the target country.
"""

#llm 연동
llm_access_key = "your_api_key_here"
genai.configure(api_key=llm_access_key)
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash', # 최신 모델 권장
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.2
    )
)
# gemini-2.5-flash-lite
# gemini-2.5-flash
# gemini-3.1-flash-lite-preview

# 국가 추가시 이쪽에도 설정할 것
CATEGORY_MAP = {
        "visa": {"en": 1435, "vi": 1433, "id": 1441, "ne": 1439, "uz": 1437},
        "tax":  {"en": 1453, "vi": 1455, "id": 1457, "ne": 1459, "uz": 1461},
        "life": {"en": 1471, "vi": 1469, "id": 1467, "ne": 1465, "uz": 1463},
        "job":  {"en": 1443, "vi": 1445, "id": 1447, "ne": 1449, "uz": 1451},
    }

# llm 호출(타이틀, 프롬프트 구분)
async def get_gemini_title(keyword_guide):
    
    # 1. 빈 배열이거나 None이면 즉시 리턴 (또는 특정 값 리턴)
    if not keyword_guide:
        logging.info("keyword_guide가 비어있습니다. 기본 주제로 시작하거나 작업을 중단합니다.")
        # 아예 중단하고 싶다면 return None
        # 처음이라서 기본 주제를 받고 싶다면 이 if문을 지우거나 아래 prompt를 그대로 실행하세요.
        # 여기서는 요청하신 대로 '즉시 리턴' 구조로 작성합니다.
        return None 

    history_str = ", ".join(keyword_guide)
    
    prompt = f"""
        당신은 한국 생활 가이드 전문가입니다.
        아래 [기존 주제 리스트]에 없는 새로운 주제를 하나 선정해주세요.
        주제를 선택할 때는 외국인 노동자(필리핀, 베트남, 인도네시아, 네팔, 우즈베키스탄)들과 관련이 있거나,
        전 세계 외국인 노동자와 관련 있는 주제를 선정하세요.
        비자(visa), 라이프(life), 취업(job) 중 하나의 카테고리를 선택하여 타이틀을 작성하세요.

        [기존 주제 리스트]: {history_str}

        [요구사항]:
        1. 반드시 한국어로 하나의 제목만 선정합니다.
        2. 카테고리는 visa, life, job 중 하나만 선택합니다.
        3. 결과는 반드시 아래 JSON 형식으로만 답변하고, 다른 설명은 하지 마세요.

        {{
            "title": "제목",
            "category": "visa/life/job 중 하나"
        }}
    """
    
    try:
        # 모델 호출 (기존에 정의하신 model 변수 사용)
        response = model.generate_content(prompt)
        res_text = response.text.strip()

        # 1. 마크다운 코드 블록 제거 및 순수 JSON 추출
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()

        # 2. 정규식을 사용하여 중괄호 { } 사이의 내용만 추출 (파싱 안정성 확보)
        json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
        
        if json_match:
            # strict=False를 주어 제어 문자 오류를 방지합니다.
            return json.loads(json_match.group(), strict=False)
        else:
            logging.error("JSON 형식을 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        logging.error(f"주제 생성 중 오류 발생: {str(e)}")
        return None


# llm 호출 함수
async def get_gemini_content(title, target_country):
    # 국가별 언어 명시적 매핑 (LLM의 혼동 방지)
    lang_map = {
        "English": "English",
        "Vietnam": "Vietnamese",
        "Indonesia": "Indonesian",
        "Nepal": "Nepali",
        "Uzbekistan": "Uzbek"
    }
    target_lang = lang_map.get(target_country, "English")

    user_prompt = f"""
    Write a detailed Korea life guide for people from {target_country} in {target_lang}.

    [Topic]: {title}
    
    [Requirements]:
    1. Content Length: Over 3,000 characters with professional legal/practical information.
    2. Tone: Extremely friendly and warm, like a close friend talking to the user.
    3. Localization: Localization the 'translated_title' to be attractive to {target_country} citizens.
    4. Structure: Use card-style UI with emojis and representative colors for {target_country}.

    [Output Format]:
    {{
        "translated_title": "Attractive title in {target_lang}",
        "final_content": "HTML content in {target_lang} (Minified, only single quotes for styles)",
        "seo_title": "SEO Title in {target_lang}",
        "seo_desc": "SEO Description in {target_lang}",
        "tags": ["tag1", "tag2", ..., "tag10"]
    }}
    
    REMEMBER: NO KOREAN. ONLY {target_lang}.
    """

    try:
        # 모델 호출 (이미 system_instruction이 적용된 상태)
        response = model.generate_content(user_prompt)
        res_text = response.text.strip()

        # 마크다운 블록 제거
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()

        json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(), strict=False)
            
    except Exception as e:
        logging.error(f"LLM Error ({target_country}): {str(e)}")
        return None

# 워드프레스에 태그가 없으면 생성하고, 있으면 ID를 가져오는 함수
def get_or_create_tags(tag_names, lang_code):
    tag_ids = []
    for name in tag_names:
        # 1. 기존 태그 검색
        search_res = requests.get(f"{WP_URL}/tags?search={name}&lang={lang_code}", auth=auth)
        existing_tags = search_res.json()
        
        if search_res.status_code == 200 and existing_tags:
            tag_ids.append(existing_tags[0]['id'])
        else:
            # 2. 없으면 새로 생성
            create_res = requests.post(f"{WP_URL}/tags", json={"name": name, "lang": lang_code}, auth=auth)
            if create_res.status_code == 201:
                tag_ids.append(create_res.json()['id'])
    return tag_ids

@app.get("/publish-all")
async def publish_all():
    countries = [
        {"name": "English", "code": "en"},
        {"name": "Vietnam", "code": "vi"},
        {"name": "Indonesia", "code": "id"},
        {"name": "Nepal", "code": "ne"},
        {"name": "Uzbekistan", "code": "uz"},
    ]
    
    post_ids = {} # Polylang 연결용 { "en": 123, "vi": 124 ... }
    results = []

    keyword_guide = get_published_history()
    
    res = await get_gemini_title(keyword_guide)
    title = res['title']
    category = res['category']

    save_to_history(title)

    for country in countries:
        lang = country['code']
        # 1. LLM으로 각 언어별(영어 포함) 콘텐츠 생성
        generated = await get_gemini_content(title, country['name'])
        if not generated: return "error"

        # 2. 태그 처리
        tag_ids = get_or_create_tags(generated.get('tags', []), lang)
        cat_id = CATEGORY_MAP.get(category, {}).get(lang)

        # 3. 워드프레스 포스팅 페이로드 (성공했던 SEO 필드 포함)
        payload = {
            "title": generated['translated_title'],
            "content": generated['final_content'],
            "status": "publish",
            "categories": [cat_id] if cat_id else [],
            "tags": tag_ids,
            "lang": lang,
            "template": "wp-custom-template-2",
            # 테스트에서 성공한 키값으로 설정 (Yoast 기준)
            "yoast_title": generated['seo_title'], 
            "yoast_desc": generated['seo_desc']
        }

        # 4. 발행
        res = requests.post(f"{WP_URL}/posts?lang={lang}", json=payload, auth=auth)
        
        if res.status_code == 201:
            new_id = res.json().get("id")
            post_ids[lang] = new_id
            results.append({country['name']: "성공", "id": new_id})
            logging.info(f"발행 성공: {country['name']} (ID: {new_id})")
        else:
            logging.error(f"발행 실패: {country['name']} - {res.text}")

        # API 과부하 방지 (영어 발행 후에도 약간 대기)
        time.sleep(60)

    # 5. [중요] 모든 글이 생성된 후 Polylang으로 상호 연결
    if len(post_ids) > 1:
        for lang, p_id in post_ids.items():
            link_payload = {"translations": post_ids}
            requests.post(f"{WP_URL}/posts/{p_id}?lang={lang}", json=link_payload, auth=auth)
        logging.info("Polylang 모든 언어 연결 완료")

    return {"message": "전체 공정 완료", "details": results}

@app.get('/')
def health_check():
    return "health_ok"

# 현재 api키로 사용 가능한 모델 검색
@app.get('/model-check')
def model_check():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            logging.info(f"사용 가능한 모델: {m.name}")

# .txt 파일 확인
@app.get('/file-check')
def file_chekc():
    return get_published_history()
        
    
# 실행 명령어
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)