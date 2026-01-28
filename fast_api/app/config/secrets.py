import os
from fastapi_mail import ConnectionConfig

JWT_SECRET_KEY = os.getenv("SECRET_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

missing = []
if not JWT_SECRET_KEY:
    missing.append("SECRET_KEY")
if not OPENAI_API_KEY:
    missing.append("OPENAI_API_KEY")
    
if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")