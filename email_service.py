import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Email Configuration
# SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
# SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
# SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'support@toolsmetric.com')
# SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '&l~yrU@k8=Y')
# ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'support@toolsmetric.com')
SMTP_HOST = os.environ['SMTP_HOST']
SMTP_PORT = int(os.environ['SMTP_PORT'])
SMTP_EMAIL = os.environ['SMTP_EMAIL']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
SITE_NAME = "ToolsMetric"
SITE_URL = "https://toolsmetric.com"


def send_email(to_email: str, subject: str, html_content: str, plain_content: Optional[str] = None) -> bool:
    """Send an email using SMTP with SSL"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SITE_NAME} <{SMTP_EMAIL}>"
        msg['To'] = to_email

        # Plain text version
        if plain_content:
            part1 = MIMEText(plain_content, 'plain')
            msg.attach(part1)

        # HTML version
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)

        # Create SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        # Connect and send
        # with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        #     server.login(SMTP_EMAIL, SMTP_PASSWORD)
        #     server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


# Email Templates

def get_base_template(content: str) -> str:
    """Base email template with consistent styling"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse;">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 30px; background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); border-radius: 16px 16px 0 0; text-align: center;">
                                <h1 style="margin: 0; color: white; font-size: 24px; font-weight: bold;">
                                    {SITE_NAME}
                                </h1>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px; background-color: white;">
                                {content}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px; background-color: #f9fafb; border-radius: 0 0 16px 16px; text-align: center;">
                                <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 14px;">
                                    © 2026 {SITE_NAME}. All rights reserved.
                                </p>
                                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                    <a href="{SITE_URL}" style="color: #10b981; text-decoration: none;">Visit our website</a>
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


# ===== USER AUTHENTICATION EMAILS =====

def send_welcome_email(to_email: str, user_name: str) -> bool:
    """Send welcome email to new user"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">Welcome to {SITE_NAME}! 🎉</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {user_name},
        </p>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Thank you for joining {SITE_NAME}! We're excited to have you on board.
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            With your account, you can now:
        </p>
        <ul style="margin: 0 0 25px 0; padding-left: 20px; color: #4b5563; font-size: 16px; line-height: 1.8;">
            <li>Write reviews for your favorite tools</li>
            <li>Submit new tools for listing</li>
            <li>Compare tools side by side</li>
            <li>Save your favorite tools</li>
        </ul>
        <a href="{SITE_URL}/tools" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
            Explore Tools
        </a>
    """
    return send_email(to_email, f"Welcome to {SITE_NAME}! 🎉", get_base_template(content))


def send_login_notification(to_email: str, user_name: str, login_time: str, ip_address: str = "Unknown") -> bool:
    """Send login notification for security"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">New Login Detected 🔐</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {user_name},
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            We noticed a new login to your {SITE_NAME} account:
        </p>
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
            <p style="margin: 0 0 10px 0; color: #4b5563; font-size: 14px;">
                <strong>Time:</strong> {login_time}
            </p>
            <p style="margin: 0; color: #4b5563; font-size: 14px;">
                <strong>IP Address:</strong> {ip_address}
            </p>
        </div>
        <p style="margin: 0; color: #6b7280; font-size: 14px;">
            If this wasn't you, please secure your account immediately by changing your password.
        </p>
    """
    return send_email(to_email, f"New Login to Your {SITE_NAME} Account", get_base_template(content))


# ===== TOOL SUBMISSION EMAILS =====

def send_submission_received(to_email: str, submitter_name: str, tool_name: str, submission_id: str) -> bool:
    """Send confirmation when tool is submitted"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">Submission Received! 📬</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {submitter_name},
        </p>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Thank you for submitting <strong>{tool_name}</strong> to {SITE_NAME}!
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Our team will review your submission and get back to you within 2-3 business days.
        </p>
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
            <p style="margin: 0 0 5px 0; color: #6b7280; font-size: 12px; text-transform: uppercase;">
                Submission ID
            </p>
            <p style="margin: 0; color: #111827; font-size: 14px; font-family: monospace;">
                {submission_id}
            </p>
        </div>
        <p style="margin: 0; color: #6b7280; font-size: 14px;">
            We'll notify you once the review is complete.
        </p>
    """
    return send_email(to_email, f"Submission Received: {tool_name}", get_base_template(content))


def send_tool_approved(to_email: str, submitter_name: str, tool_name: str, tool_slug: str) -> bool:
    """Send notification when tool is approved"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">Your Tool is Live! 🎉</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {submitter_name},
        </p>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Great news! <strong>{tool_name}</strong> has been approved and is now live on {SITE_NAME}!
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Your tool is now visible to thousands of businesses looking for the right software solutions.
        </p>
        <a href="{SITE_URL}/tool/{tool_slug}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
            View Your Tool
        </a>
        <p style="margin: 25px 0 0 0; color: #6b7280; font-size: 14px;">
            Thank you for contributing to our community!
        </p>
    """
    return send_email(to_email, f"🎉 {tool_name} is Now Live on {SITE_NAME}!", get_base_template(content))


def send_tool_rejected(to_email: str, submitter_name: str, tool_name: str, reason: str = "") -> bool:
    """Send notification when tool is rejected"""
    reason_section = ""
    if reason:
        reason_section = f"""
        <div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #ef4444;">
            <p style="margin: 0 0 5px 0; color: #991b1b; font-size: 12px; text-transform: uppercase; font-weight: 600;">
                Reason
            </p>
            <p style="margin: 0; color: #7f1d1d; font-size: 14px;">
                {reason}
            </p>
        </div>
        """
    
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">Submission Update</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {submitter_name},
        </p>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Thank you for submitting <strong>{tool_name}</strong> to {SITE_NAME}.
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            After careful review, we were unable to approve this submission at this time.
        </p>
        {reason_section}
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            You're welcome to address the feedback and submit again. We appreciate your interest in {SITE_NAME}!
        </p>
        <a href="{SITE_URL}/submit-tool" style="display: inline-block; padding: 14px 28px; background-color: #6b7280; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
            Submit Again
        </a>
    """
    return send_email(to_email, f"Submission Update: {tool_name}", get_base_template(content))


# ===== REVIEW EMAILS =====

def send_review_posted(to_email: str, user_name: str, tool_name: str, tool_slug: str) -> bool:
    """Send confirmation when review is posted"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">Review Posted! ⭐</h2>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Hi {user_name},
        </p>
        <p style="margin: 0 0 15px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Your review for <strong>{tool_name}</strong> has been posted successfully!
        </p>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            Thank you for sharing your experience with the community. Your feedback helps others make better decisions.
        </p>
        <a href="{SITE_URL}/tool/{tool_slug}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
            View Your Review
        </a>
    """
    return send_email(to_email, f"Your Review for {tool_name} is Live!", get_base_template(content))


# ===== ADMIN NOTIFICATION EMAILS =====

def send_admin_new_submission(tool_name: str, submitter_name: str, submitter_email: str, submission_id: str) -> bool:
    """Notify admin of new tool submission"""
    content = f"""
        <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 22px;">New Tool Submission 🔔</h2>
        <p style="margin: 0 0 25px 0; color: #4b5563; font-size: 16px; line-height: 1.6;">
            A new tool has been submitted for review:
        </p>
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
            <p style="margin: 0 0 10px 0; color: #4b5563; font-size: 14px;">
                <strong>Tool Name:</strong> {tool_name}
            </p>
            <p style="margin: 0 0 10px 0; color: #4b5563; font-size: 14px;">
                <strong>Submitted By:</strong> {submitter_name}
            </p>
            <p style="margin: 0 0 10px 0; color: #4b5563; font-size: 14px;">
                <strong>Email:</strong> {submitter_email}
            </p>
            <p style="margin: 0; color: #4b5563; font-size: 14px;">
                <strong>ID:</strong> <code style="background: #e5e7eb; padding: 2px 6px; border-radius: 4px;">{submission_id}</code>
            </p>
        </div>
        <a href="{SITE_URL}/admin/submissions" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
            Review Submission
        </a>
    """
    return send_email(ADMIN_EMAIL, f"New Submission: {tool_name}", get_base_template(content))
