"""
app/services/email_service.py

Email service for NourishGraph using Resend.

Configuration via .env:
    RESEND_API_KEY=re_xxxxxxxxxxxxx
    FRONTEND_URL=https://nourishgraph.com (or http://localhost:5173 for dev)
    
Usage:
    from app.services.email_service import send_password_reset_email
    
    success = await send_password_reset_email("user@example.com", "abc123token")
"""

import os
from typing import Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Try to import resend
try:
    import resend
    HAS_RESEND = True
except ImportError:
    HAS_RESEND = False
    print("[WARN] resend not installed. Install with: pip install resend")


# ============================================================
# CONFIGURATION
# ============================================================

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
# Use Resend's test email for unverified domains
FROM_EMAIL = os.getenv("FROM_EMAIL", "NourishGraph <onboarding@resend.dev>")

# Initialize resend if available
if HAS_RESEND and RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# ============================================================
# EMAIL TEMPLATES
# ============================================================

def get_password_reset_email_html(reset_link: str, user_name: str = "there") -> str:
    """Generate HTML email for password reset."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password - NourishGraph</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f5;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 20px 40px; text-align: center;">
                            <div style="font-size: 32px; margin-bottom: 10px;">🥗</div>
                            <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #10b981;">NourishGraph</h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 20px 40px;">
                            <h2 style="margin: 0 0 20px 0; font-size: 20px; font-weight: 600; color: #1f2937;">Reset Your Password</h2>
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">
                                Hi {user_name},
                            </p>
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">
                                We received a request to reset your password for your NourishGraph account. Click the button below to create a new password:
                            </p>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 30px 0;">
                                <tr>
                                    <td style="border-radius: 8px; background-color: #10b981;">
                                        <a href="{reset_link}" target="_blank" style="display: inline-block; padding: 14px 32px; font-size: 16px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 8px;">
                                            Reset Password
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #6b7280;">
                                This link will expire in <strong>1 hour</strong> for security reasons.
                            </p>
                            
                            <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #6b7280;">
                                If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
                            </p>
                            
                            <!-- Fallback Link -->
                            <div style="margin-top: 30px; padding: 20px; background-color: #f9fafb; border-radius: 8px;">
                                <p style="margin: 0 0 10px 0; font-size: 12px; color: #6b7280;">
                                    If the button doesn't work, copy and paste this link into your browser:
                                </p>
                                <p style="margin: 0; font-size: 12px; word-break: break-all;">
                                    <a href="{reset_link}" style="color: #10b981;">{reset_link}</a>
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px 40px; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center;">
                                © 2024 NourishGraph. All rights reserved.<br>
                                Your AI-powered nutrition companion.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_password_reset_email_text(reset_link: str, user_name: str = "there") -> str:
    """Generate plain text email for password reset."""
    return f"""
Reset Your Password - NourishGraph

Hi {user_name},

We received a request to reset your password for your NourishGraph account. 

Click the link below to create a new password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

---
© 2024 NourishGraph
Your AI-powered nutrition companion.
"""


# ============================================================
# EMAIL FUNCTIONS
# ============================================================

async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send a password reset email.
    
    Args:
        to_email: Recipient email address
        reset_token: The password reset token
        user_name: Optional user name for personalization
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    if not HAS_RESEND:
        print(f"[WARN] Resend not installed. Would send reset email to: {to_email}")
        return False
    
    if not RESEND_API_KEY:
        print(f"[WARN] RESEND_API_KEY not configured. Would send reset email to: {to_email}")
        # In development, print the reset link
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        print(f"[DEV] Reset link: {reset_link}")
        return False
    
    try:
        # Build reset link
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        
        # Personalize name
        display_name = user_name or "there"
        
        # Send email via Resend
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset Your Password - NourishGraph",
            "html": get_password_reset_email_html(reset_link, display_name),
            "text": get_password_reset_email_text(reset_link, display_name),
        }
        
        email = resend.Emails.send(params)
        
        print(f"✅ Password reset email sent to {to_email} (ID: {email.get('id', 'N/A')})")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to send password reset email to {to_email}: {e}")
        return False


async def send_welcome_email(
    to_email: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send a welcome email to new users.
    
    Args:
        to_email: Recipient email address
        user_name: Optional user name for personalization
        
    Returns:
        True if email was sent successfully, False otherwise
    """
    if not HAS_RESEND or not RESEND_API_KEY:
        print(f"[WARN] Email not configured. Would send welcome email to: {to_email}")
        return False
    
    try:
        display_name = user_name or "there"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome to NourishGraph!</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f5;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <tr>
                        <td style="padding: 40px; text-align: center;">
                            <div style="font-size: 48px; margin-bottom: 10px;">🥗</div>
                            <h1 style="margin: 0 0 20px 0; font-size: 28px; font-weight: 700; color: #10b981;">Welcome to NourishGraph!</h1>
                            <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">
                                Hi {display_name}, we're excited to have you on board!
                            </p>
                            <p style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #4b5563;">
                                NourishGraph is your AI-powered nutrition companion, providing science-backed advice and personalized meal plans.
                            </p>
                            <a href="{FRONTEND_URL}" style="display: inline-block; padding: 14px 32px; font-size: 16px; font-weight: 600; color: #ffffff; background-color: #10b981; text-decoration: none; border-radius: 8px;">
                                Get Started
                            </a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Welcome to NourishGraph! 🥗",
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Welcome email sent to {to_email} (ID: {email.get('id', 'N/A')})")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to send welcome email to {to_email}: {e}")
        return False
