from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from app.api import auth
from app.api import prompt
from app.api import user

# uvicorn app.main:app --reload

app = FastAPI()

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(prompt.router, prefix="/api/prompt", tags=["Prompt"])
app.include_router(user.router, prefix="/api/user", tags=["User"])

@app.get("/health")
def health():
    return {"status": "ok"}
