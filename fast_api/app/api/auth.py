from fastapi import APIRouter, HTTPException, Depends, Header
from app.config.firebase import db
from app.security.security import hash_password, decode_token, verify_token_with_refresh, create_access_token, create_refresh_token
from passlib.context import CryptContext
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.cloud.firestore import Transaction
from google.cloud import firestore
from app.security.email import generate_verification_code, send_verification_email
import re
from pydantic import BaseModel, EmailStr

router = APIRouter()

class SendVerificationRequest(BaseModel):
    email: EmailStr
    time_zone: str

class CheckVerificationRequest(BaseModel):
    email: EmailStr
    time_zone: str
    code: str

class SignupVerificationRequest(BaseModel):
    email: EmailStr
    time_zone: str
    password: str
    name: str
    info_agree: bool

class LoginVerificationRequest(BaseModel):
    email: EmailStr
    password: str
    
class LogoutVerificationRequest(BaseModel):
    email: EmailStr

# auth part

# send email
@router.post("/send-verification")
async def send_verification_code(req: SendVerificationRequest):
    email = req.email
    time_zone = req.time_zone
    
    users = db.collection("users").where("email", "==", email).limit(1).get()
    
    if users:
        raise HTTPException(400, "Email already registered")
    
    code = generate_verification_code()
    
    now = datetime.now(ZoneInfo(time_zone))
    now_utc = now.astimezone(ZoneInfo("UTC"))
    
    validate_ref = db.collection("validate").document(email)
    validate_doc = validate_ref.get()
    
    if validate_doc.exists:
        validate_data = validate_doc.to_dict()
        create_at = validate_data.get("create_at")
        
        if create_at:
            if now_utc - create_at < timedelta(minutes=3):
                raise HTTPException(429, "Please press the send button again after 3 minutes.")
        
    await send_verification_email(email, code)
    
    validate_ref.set({
        "create_at": now_utc,
        "code": code,
    })
        
    return {"message": "email send success"}
        
#email code check
@router.post("/send-verification/check")
def send_verification_check(req: CheckVerificationRequest):
    email = req.email
    code = req.code
    time_zone = req.time_zone
    
    validate_ref = db.collection("validate").document(email)
    validate_doc = validate_ref.get()
    
    if validate_doc.exists:
        return {"message": "Please send the authentication number first."}
    
    now = datetime.now(ZoneInfo(time_zone))
    now_utc = now.astimezone(ZoneInfo("UTC"))
    
    validate_dict = validate_doc.to_dict()
    
    db_code = validate_dict.get("code")
    create_at = validate_dict.get("create_at")
    
    if (db_code == code and now_utc - create_at <= timedelta(minutes=5)):
        validate_ref.delete()
        return {"message": "Email code validate successful"}
    
    validate_ref.delete()
    return {"message": "Email code validate failed"}
    

# signup logic
@router.post("/signup")
def signup(req: SignupVerificationRequest):
    email = req.email
    password = req.password
    time_zone = req.time_zone
    name = req.name
    info_agree = req.info_agree

    try:
        create_date = datetime.now(ZoneInfo(time_zone))
        create_at = create_date.astimezone(ZoneInfo("UTC"))
    except Exception:
        raise HTTPException(400, f"Invalid timezone: {time_zone}")

    password_hash = hash_password(password)

    users_ref = db.collection("users")
    email_index_ref = db.collection("user_emails").document(email)
    
    @firestore.transactional
    def signup_transaction(transaction: Transaction):
        email_snapshot = email_index_ref.get(transaction=transaction)
        if email_snapshot.exists:
            raise RuntimeError("Email already exists")
        
        user_ref = users_ref.document()
        
        transaction.set(user_ref, {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "create_date": create_at,
            "last_login_date": None,
            "time_zone": time_zone,
            "provider": "local",
            "joi_point": 0,
            "role": "USER",
            "info_agree": info_agree,
            "phq9_complete": False,
            "gad7_complete": False,
            "deep_complete": False,
        })
        
        transaction.set(email_index_ref, {
            "user_id": user_ref.id,
        })
    
    try:
        transaction = db.transaction()
        signup_transaction(transaction)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
    
    return {"message": "Signup successful"}

# login logic
@router.post("/login")
def login(req: LoginVerificationRequest):
    email = req.email
    password = req.password
    
    users = db.collection("users").where("email", "==", email).limit(1).get()
    if not users:
        raise HTTPException(401, "Invalid credentials")
    
    user_doc = users[0]
    user_data = user_doc.to_dict()
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(password, user_data.get("password_hash")):
        raise HTTPException(401, "Password is different")

    token_data = {
        "user_id": user_doc.id,
        "email": email,
        "role": user_data.get("role"),
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    if user_data.get("last_login_date") is not None:
        date = datetime.now(ZoneInfo(user_data.get("time_zone", "UTC")))
        date_utc = date.astimezone(ZoneInfo("UTC"))
        last_date = user_data.get("last_login_date", None)
        point = user_data.get("joi_point", 0)
        
        days_diff = (date_utc.date() - last_date.date()).days
        
        if days_diff >= 1:
            point += 5

        db.collection("users").document(user_doc.id).update({
            "last_login_date": date,
            "joi_point": point,
            "refresh_token": refresh_token,
            "phq9_complete": False,
            "gad7_complete": False,
            "deep_complete": False,
        })
        user_data["phq9_complete"] = False
        user_data["gad7_complete"] = False
        user_data["deep_complete"] = False
    else:
        point = 5
        date = datetime.now(ZoneInfo(user_data.get("time_zone", "UTC")))
        db.collection("users").document(user_doc.id).update({
            "last_login_date": date,
            "joi_point": point,
            "refresh_token": refresh_token,
        })
    user_data["last_login_date"] = date
    user_data["joi_point"] = point
    user_data["id"] = user_doc.id
    user_data.pop("password_hash", None)
    user_data.pop("refresh_token", None)
    
    return {
        "user": user_data,
        "message": "Login successful",
        "access_token": access_token,
    }
    
# logout logic
@router.post("/logout")
def logout(req: LogoutVerificationRequest):
    email = req.email
    
    docs = db.collection("users").where("email", "==", email).limit(1).get()
    
    doc = docs[0]
    
    if not doc:
        raise HTTPException(404, "User not found")
    
    doc.reference.update({
        "refresh_token": None
    })

    return {"message": "Logged out successfully"}