import os
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_resend_email(to_email: str, subject: str, html_content: str) -> tuple[bool, str]:
    """
    Sends an email using the Resend API via HTTP POST.
    Completely bypasses Django's SMTP backend to avoid Render port blocking.
    """
    if to_email.endswith("@loadtest.com"):
        logger.info(f"Bypassing email for load test user: {to_email}")
        return True, "Load test bypass"

    api_key = getattr(settings, 'RESEND_API_KEY', os.getenv('RESEND_API_KEY'))
    if not api_key:
        logger.error("RESEND_API_KEY is not configured.")
        return False, "API Key missing"

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": getattr(settings, 'DEFAULT_FROM_EMAIL', "onboarding@resend.dev"),
        "to": to_email,
        "subject": subject,
        "html": html_content
    }

    try:
        # Standard 5-second timeout for external API calls
        response = requests.post(url, json=payload, headers=headers, timeout=5.0)
        
        if response.status_code in [200, 201]:
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Success"
        else:
            error_msg = f"Resend API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return False, error_msg

    except requests.exceptions.Timeout:
        error_msg = f"Resend API Error: Request timed out for {to_email}"
        logger.error(error_msg)
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Resend API Error: Network failure - {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_email(to_email: str, otp: str) -> bool:
    """
    Standard helper wrapper required by the specification.
    Returns True if email sent, False otherwise.
    """
    subject = "GreenLoop Login OTP"
    html_content = f"<p>Your GreenLoop login OTP is <strong>{otp}</strong>. It is valid for 5 minutes.</p>"
    success, _ = send_resend_email(to_email, subject, html_content)
    return success
