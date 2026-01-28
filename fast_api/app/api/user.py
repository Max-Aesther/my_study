from fastapi import APIRouter, HTTPException, Depends
from app.security.security import get_current_user
from app.config.firebase import db
from datetime import datetime
from zoneinfo import ZoneInfo
from google.cloud.firestore import Transaction
from pydantic import BaseModel

router = APIRouter()

class PHQ9VerificationRequest(BaseModel):
    phq9_data: list[str]

@router.get("/userdata")
def get_user_data(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    user_doc = db.collection("users").document(user_id).get()
    
    user_data = user_doc.to_dict()
    user_data.pop("password_hash", None)
    user_data.pop("refresh_token", None)
    
    return {"user": user_data}
    
@router.post("/phq9/save")
def user_phq9_save(req: PHQ9VerificationRequest, current_user: dict = Depends(get_current_user)):
    phq9_data = req.phq9_data
    
    user_id = current_user["user_id"]
    time_zone = current_user["time_zone"]
    now = datetime.now(ZoneInfo(time_zone))
    now_utc = now.astimezone(ZoneInfo("UTC"))
    today_str = now_utc.strftime("%Y-%m-%d")
    
    phq9_ref = db.collection("users").document(user_id).collection("phq9_assessments").document(today_str)
    
    def phq9_data_transaction(transaction: Transaction):
        snapshot = phq9_ref.get(transaction = transaction)
        if snapshot.exists:
            raise HTTPException(500, "PHQ9_data save failed")
        
        
    
    
# @router.get("/admindata")
# def get_admin_data(
#     current_user: dict = Depends(require_role("admin"))
# ):
#     return {
#         "admin_info": "admin_data",
#         "sensitive_data": "info"
#     }


# user check
# @router.get("/users/by-email")
# def get_user_by_email(
#     email: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     # admin email
#     if current_user.get("email") != email and current_user.get("role") != "admin":
#         raise HTTPException(403, "Access denied")
    
#     users_ref = db.collection("users").where("email", "==", email).limit(1).stream()
    
#     for user_doc in users_ref:
#         return user_doc.to_dict()
    
#     raise HTTPException(404, "User not found")