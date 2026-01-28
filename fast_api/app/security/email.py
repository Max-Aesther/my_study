from fastapi_mail import MessageSchema, FastMail
from app.config.secrets import mail_config
import random
import string

def generate_verification_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

async def send_verification_email(email: str, code: str):
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">✉️ SAMPLE</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Email Verification</p>
                </div>
                
                <!-- Main -->
                <div style="padding: 40px 30px;">
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">hello,</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        We will provide you with the authentication number for sample membership registration.
                    </p>
                    
                    <!-- authentication number box -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; margin: 30px 0; border-radius: 8px;">
                        <p style="color: rgba(255,255,255,0.8); margin: 0 0 10px 0; font-size: 14px;">authentication number</p>
                        <h1 style="color: white; margin: 0; letter-spacing: 10px; font-size: 42px; font-weight: bold;">{code}</h1>
                    </div>
                    
                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px;">
                        <p style="color: #856404; margin: 0; font-size: 14px;">
                            This authentication number is <strong>valid for 5 minutes.</strong>
                        </p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6; margin-top: 30px;">
                        Please enter the verification number to complete email verification.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8f9fa; padding: 20px 30px; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 12px; margin: 0; line-height: 1.6;">
                        You may ignore this email unless you requested it.<br>
                    </p>
                    <p style="color: #adb5bd; font-size: 11px; margin: 10px 0 0 0;">
                        © 2026 sample. All rights reserved.
                    </p>
                </div>
                
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject="[sample] Email verification number",
        recipients=[email],
        body=html,
        subtype="html"
    )
    
    fm = FastMail(mail_config)
    await fm.send_message(message)