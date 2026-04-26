import os
import pickle
import uuid
import asyncio
import edge_tts
import json
import textwrap
import requests
import urllib.parse
import logging
from PIL import Image
from google import genai
from fastapi import FastAPI, BackgroundTasks, Body
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import AudioFileClip, CompositeVideoClip, TextClip, ImageClip, concatenate_audioclips

os.environ["IMAGEMAGICK_BINARY"] = "/opt/homebrew/bin/convert"

app = FastAPI()

GENAI_API_KEY = "YOUR_GENAI_API_KEY"
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_PICKLE = "token.pickle"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
UPLOAD_DIR = "temp_assets"

client = genai.Client(api_key=GENAI_API_KEY)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ─── 유튜브 인증 ──────────────────────────────────────────
def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)


# ─── 이미지 생성 (Pollinations) ───────────────────────────
async def generate_image_pollinations(prompt: str, img_path: str, idx: int,
                                       max_retries: int = 3, timeout: int = 90) -> bool:
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1080&height=1920&nologo=true&seed={idx + 100}&model=flux"
    )
    for attempt in range(1, max_retries + 1):
        try:
            log.info(f"  [이미지 {idx}] 시도 {attempt}/{max_retries} ...")
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            with open(img_path, 'wb') as f:
                f.write(resp.content)
            log.info(f"  [이미지 {idx}] 성공")
            return True
        except Exception as e:
            log.warning(f"  [이미지 {idx}] 실패 ({e})")
            if attempt < max_retries:
                await asyncio.sleep(3)

    log.error(f"  [이미지 {idx}] 모든 시도 실패 → 더미 이미지")
    Image.new('RGB', (1080, 1920), color=(30, 30, 30)).save(img_path)
    return False


# ─── 자막 줄바꿈 ──────────────────────────────────────────
def wrap_subtitle(text: str, max_words: int = 10, max_chars: int = 30, max_lines: int = 3) -> str:
    words = text.split()
    if len(words) > max_words:
        text = ' '.join(words[:max_words]) + '...'
    lines = textwrap.wrap(text, width=max_chars)
    lines = lines[:max_lines]
    return "\n".join(lines)


# ─── 메인 파이프라인 ──────────────────────────────────────
async def full_pipeline_worker(topic: str, lang: str):
    job_id = str(uuid.uuid4())
    video_path = os.path.join(UPLOAD_DIR, f"{job_id}.mp4")
    temp_files = []
    scene_audios = []

    try:
        # 1. 대본 생성 ─────────────────────────────────────
        log.info("1. 대본 생성 중...")
        prompt = f"""
        Topic: {topic}. Language: {lang}.
        Create a YouTube Shorts script divided into exactly 11 scenes. 
        The goal is to reach a 45-second duration with normal speaking speed.

        STRICT RULES:
        1. Each scene's 'text' must be between 7 and 10 words. (Crucial for timing!)
        2. Use simple, direct English for a global audience.
        3. Each sentence must be a complete, punchy thought.
        4. 'img_prompt' must be in English, cinematic, and photorealistic.
            Avoid drawing "aliens". Focus on "International professionals in Korea" or relevant objects (Bank, Passport, Card).
        5. STRICT TERMINOLOGY:
            - NEVER use the word "Alien" even in the context of "Alien Registration Card".
            - ALWAYS replace "Alien Registration Card" with "Residence Card" or "Foreigner ID".
            - Use "International resident", "Global worker", or "Foreigner" instead of "Alien".

        Return ONLY a JSON list with exactly 11 items.
        """
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        script_data = json.loads(response.text)
        if isinstance(script_data, dict) and 'scenes' in script_data:
            script_data = script_data['scenes']
        log.info(f"   → {len(script_data)}개 장면 생성됨")

        ending_text = "Full Guide? Link in Profile!"

        script_data.append({
            "text": ending_text,
            "img_prompt": "A clean, modern laptop screen displaying a professional blog with helpful guides, soft cinematic lighting, 8k photorealistic"
        })

        # 2. 장면별 음성 생성 (싱크 맞추기 위해 개별 생성) ──
        log.info("2. 장면별 음성 생성 중...")
        voice = "ko-KR-InJoonNeural" if lang == "ko" else "en-US-AvaNeural"

        for idx, item in enumerate(script_data):
            audio_file = os.path.join(UPLOAD_DIR, f"{job_id}_audio_{idx}.mp3")
            temp_files.append(audio_file)
            await edge_tts.Communicate(item['text'], voice).save(audio_file)
            clip = AudioFileClip(audio_file)
            scene_audios.append(clip)
            log.info(f"   장면 {idx+1} 음성: {clip.duration:.1f}초")

        # 3. 이미지 생성 + 클립 조립 ────────────────────────
        log.info("3. 이미지 생성 및 클립 조립 중...")
        final_clips = []
        start_t = 0.0

        for idx, (item, audio_clip) in enumerate(zip(script_data, scene_audios)):
            duration = audio_clip.duration

            # ── 이미지 생성 ─────────────────────────────────
            img_path = os.path.join(UPLOAD_DIR, f"{job_id}_{idx}.jpg")
            temp_files.append(img_path)
            await generate_image_pollinations(item['img_prompt'], img_path, idx)

            # ── 이미지 클립 (줌인) ───────────────────────────
            img_clip = (
                ImageClip(img_path)
                .with_duration(duration)
                .resized(height=1920)
                .with_position('center')
                .resized(lambda t: 1 + 0.03 * t)
                .with_start(start_t)
            )

            # ── 자막 클립 ────────────────────────────────────
            # max_chars=20: 한 줄 최대 20자, max_lines=3: 최대 3줄
            wrapped = wrap_subtitle(item['text'], max_chars=30, max_lines=3)
            txt_clip = (
                TextClip(
                    text=wrapped,
                    font="/System/Library/Fonts/Supplemental/AppleGothic.ttf",
                    font_size=52,
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    method='caption',
                    size=(900, 300),
                )
                .with_duration(duration)
                .with_start(start_t)
                .with_position(('center', 0.75), relative=True)
            )

            final_clips.extend([img_clip, txt_clip])
            log.info(f"   장면 {idx+1} 완료 | {start_t:.1f}s ~ {start_t+duration:.1f}s")
            start_t += duration

        # 4. 오디오 합치기 ──────────────────────────────────
        log.info("4. 오디오 합치는 중...")
        merged_audio = concatenate_audioclips(scene_audios)

        # 5. 인코딩 ─────────────────────────────────────────
        log.info("5. 인코딩 시작...")
        if not final_clips:
            log.error("생성된 클립 없음 → 중단")
            return

        video = CompositeVideoClip(final_clips, size=(1080, 1920)).with_audio(merged_audio)
        video.write_videofile(
            video_path, fps=30,
            codec="libx264", audio_codec="aac",
            threads=4, logger=None
        )
        log.info(f"   → 저장 완료: {video_path}")

        # 6. 유튜브 업로드 ──────────────────────────────────
        log.info("6. 유튜브 업로드 중...")
        youtube = get_youtube_service()
        full_text = " ".join([item['text'] for item in script_data])

        # f-string과 삼중 따옴표를 사용하여 줄바꿈과 이모지를 그대로 유지합니다.
        description_text = f"""Helping Global Workers Build Better Futures in Korea & Beyond! 🌏

        Hello! As the number of international workers grows worldwide, we are building a global support platform to empower and guide you every step of the way.

        Currently, we provide essential guides for workers from the Philippines, Vietnam, Indonesia, Nepal, and Uzbekistan who are planning to work in South Korea.

        🚀 Our Vision:
        Starting with Korea, we plan to expand our services globally. We aim to become a "Global Career Compass" for anyone seeking work opportunities in any country, not just Korea. We are also open to strategic partnerships (MOUs) with international companies to provide localized, high-quality services.

        📍 Get More Detailed Guides on Our Blog:
        Everything you need to know about working abroad is right here!
        👉 https://koreaworkguide.com 👈        

        Stay tuned as we grow into a platform that supports workers all over the world!

        #GlobalWorker #KoreaWorkGuide #VisaInfo #ForeignLabor #JobSearch #KoreaLife #GlobalTalent #Shorts

        ---
        [Video Transcript]
        {full_text}
        """

        body = {
            "snippet": {
                "title": f"{topic} #Shorts",
                "description": description_text,
                "categoryId": "22",
                "defaultLanguage": lang
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }
        media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
        youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        log.info("업로드 완료!")

    except Exception as e:
        log.exception(f"파이프라인 오류: {e}")
    finally:
        try:
            if 'video' in locals(): video.close()
            if 'merged_audio' in locals(): merged_audio.close()
            for ac in scene_audios:
                try: ac.close()
                except: pass
        except: pass

        for f in temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except Exception as e: log.warning(f"삭제 실패: {f} ({e})")

        if os.path.exists(video_path):
            try: os.remove(video_path)
            except Exception as e: log.warning(f"영상 삭제 실패: {e}")

        log.info(f"[{job_id}] 정리 완료")


# ─── API 엔드포인트 ───────────────────────────────────────
@app.post("/auto-shorts")
async def generate_shorts(
    topic: str = Body(...),
    lang: str = Body("ko"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    background_tasks.add_task(full_pipeline_worker, topic, lang)
    return {"status": "accepted", "message": f"'{topic}' 영상 생성을 시작했습니다."}