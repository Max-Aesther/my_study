from fastapi import APIRouter, HTTPException, Depends
from app.config.firebase import db
from app.config.secrets import OPENAI_API_KEY
from openai import OpenAI
from app.security.security import get_current_user
import random
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

router = APIRouter()

client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_action_items(email: str, time_zone: str):
    phq9 = []
    gad7 = []
    
    now_user_tz = datetime.now(ZoneInfo(time_zone))
    past_user_tz = now_user_tz - timedelta(days=14)
    
    now_utc = now_user_tz.astimezone(ZoneInfo("UTC"))
    past_utc = past_user_tz.astimezone(ZoneInfo("UTC"))
    
    phq9_ref = db.collection("users").document(email).collection("phq9")
    phq9_query = phq9_ref.where("complete_date", ">=", past_utc).where("complete_date", "<=", now_utc)
    phq9_docs = phq9_query.stream()
    for phq9_doc in phq9_docs:
        data = phq9_doc.to_dict()
        score = data.get("score")
        if score is not None:
            phq9.append(score)
    
    gad7_ref = db.collection("users").document(email).collection("gad7")
    gad7_query = gad7_ref.where("complete_date", ">=", past_utc).where("complete_date", "<=", now_utc)
    gad7_docs = gad7_query.stream()
    for gad7_doc in gad7_docs:
        data = gad7_doc.to_dict()
        score = data.get("score")
        if score is not None:
            gad7.append(score)
    
    prompt = f"""
    You are a mental health professional. 

    Based on the user's assessment history, suggest 5 specific action items that would help the user improve their mental health. 

    The user's PHQ-9 total scores for previous assessments are: {phq9}.
    The user's GAD-7 total scores for previous assessments are: {gad7}.
    (The length of each array represents the number of assessments, and each value is the total score of that assessment.)

    Please generate 5 actionable, practical, and concise recommendations. 
    Return the results as a JSON object with an "items" key containing an array of strings, for example:
    {{
        "items": [
            "Take a 10-minute walk each morning.",
            "Practice deep breathing exercises daily.",
            "Write down three things you are grateful for each day.",
            "Schedule regular social activities with friends.",
            "Limit social media use to 30 minutes per day."
        ]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Return ONLY a valid JSON object with an 'items' key containing exactly 5 strings. No explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=300
    )
    
    content = response.choices[0].message.content

    try:
        result = json.loads(content)
        items = result.get("items", [])
        if not items or len(items) < 2:
            raise HTTPException(500, "Invalid AI response")
        return items 
    except json.JSONDecodeError:
        raise HTTPException(500, "Invalid AI response")

@router.get("/create_action_items")
async def create_action_items(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    time_zone = current_user["time_zone"]
    now = datetime.now(ZoneInfo(time_zone))
    today = now.strftime("%Y-%m-%d")
    user_docs = db.collection("users").where("email", "==", email).limit(1).get()
    
    if not user_docs:
        raise HTTPException(404, "User not found")
    
    user_doc = user_docs[0]
    user_ref = user_doc.reference
    action_doc_ref = user_ref.collection("action_items").document(today)
    
    action_doc = action_doc_ref.get()
    if action_doc.exists:
        items = action_doc.to_dict().get("items", [])
        return {"items": items}

    new_items = await generate_action_items(email, time_zone)
    select_items = random.sample(new_items, 2)

    update_items = []
    new_utc = now.astimezone(ZoneInfo("UTC"))

    for item in select_items:
        update_items.append({
            "content": item,
            "create_date": new_utc,
            "complete": False,
            "complete_date": None
        })

    action_doc_ref.set({"items": update_items})

    return {"items": update_items}