"""
Email functionality node for the Real Estate Agent graph.

This node handles sending reports via email with PDF attachments.
"""

import re
import json
import smtplib
from typing import Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.pdfgen import canvas
from io import BytesIO
import textwrap

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from config import config
from cache import cache_manager
from ..state import State


class EmailService:
    """Service for sending email reports."""
    
    def __init__(self):
        """Initialize the email service."""
        self.sender_email = config.email.sender_email
        self.sender_password = config.email.sender_password
        self.smtp_server = config.email.smtp_server
        self.smtp_port = config.email.smtp_port
    
    def _extract_email(self, text: str) -> str:
        """Extract email address from text."""
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        return match.group(0) if match else None
    
    def _create_pdf_report(self, report: str) -> bytes:
        """Create a PDF from the report text."""
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer)
        c.setFont("Helvetica", 11)
        
        left_margin = 40
        top_y = 800
        line_height = 14
        max_width_chars = 90  # approximate wrap width
        y = top_y
        
        def new_page():
            nonlocal y
            c.showPage()
            c.setFont("Helvetica", 11)
            y = top_y
        
        for paragraph in report.splitlines():
            # wrap long lines to avoid clipping
            wrapped = textwrap.wrap(paragraph, width=max_width_chars) or [""]
            for wl in wrapped:
                if y < 40:  # near bottom -> new page
                    new_page()
                c.drawString(left_margin, y, wl)
                y -= line_height
        
        # finish PDF
        c.showPage()
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer.read()
    
    def send_report(self, report: str, recipient_email: str, subject: str = "Real Estate Report") -> Dict[str, Any]:
        """
        Send the report as a PDF attachment to the specified email address.
        
        Args:
            report: The report content to send
            recipient_email: The email address to send the report to
            subject: The subject of the email
            
        Returns:
            Dictionary with success status and message
        """
        # Debug: Print email configuration
        print(f"DEBUG: Email service - Sender: {self.sender_email}")
        print(f"DEBUG: Email service - SMTP Server: {self.smtp_server}:{self.smtp_port}")
        print(f"DEBUG: Email service - Recipient: {recipient_email}")
        
        # Check if email configuration is set
        if not self.sender_email or not self.sender_password:
            return {"ok": False, "message": "Email configuration not set. Please configure EMAIL_SENDER and EMAIL_PASSWORD in .env file."}
        
        try:
            # Create PDF from report
            pdf_bytes = self._create_pdf_report(report)
            
            # Create email message
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject
            
            # Add body
            msg.attach(MIMEText("Please find your report attached as a PDF.", "plain"))
            
            # Add PDF attachment
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", 'attachment; filename="report.pdf"')
            msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            return {"ok": True, "message": f"Report emailed to {recipient_email}."}
            
        except Exception as e:
            return {"ok": False, "message": f"Email failed: {e}"}


# Global email service instance
email_service = EmailService()


def node_email_report(state: State) -> State:
    """
    Send the report via email if requested.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with email status
    """
    # If no email requested, do nothing
    if not state.get("needs_email"):
        return state
    
    # Get user's email from database using user_id
    to_addr = ""
    user_id = state.get("user_id", "")

    print(f"DEBUG: Email node - User ID: {user_id}")
    print(f"DEBUG: Email node - Question: {state.get('question', '')}")

    question = state.get("question", "")
    extracted_email = email_service._extract_email(question)
    print(f"DEBUG: Email node - Extracted email from question: {extracted_email}")

    if extracted_email:
        to_addr = extracted_email
        print(f"DEBUG: Email node - Using extracted email: {to_addr}")
    
    elif user_id:
        try:
            # Import db_service to get user email
            from src.services.db.sql import db_service
            user_info = db_service.get_user(user_id)
            if user_info:
                to_addr = user_info.get("email", "")
                print(f"DEBUG: Email node - Found user email in database: {to_addr}")
            else:
                print(f"DEBUG: Email node - User not found in database: {user_id}")
        except Exception as e:
            print(f"DEBUG: Email node - Error getting user from database: {e}")
    
    # If no user email from database, try to extract from question as fallback
    if not to_addr:
        to_addr = email_service._extract_email(state["question"])
        print(f"DEBUG: Email node - Using email extracted from question: {to_addr}")
    
    # Debug: Print final email address being used
    print(f"DEBUG: Email node - Final email address: {to_addr}")
    
    # Get cached report if available
    cached_report = None
    candidates = []
    q = state.get("question", "") or ""
    candidates.append(q)
    
    try:
        first_msg = state.get("messages", [])[0].get("content")
        if first_msg:
            candidates.append(first_msg)
    except Exception:
        first_msg = None
    
    for key in candidates:
        if not key:
            continue
        try:
            # Use Redis get_json instead of manual JSON parsing
            snap = cache_manager.get_json("query_cache", key)
            if not snap:
                continue
            rpt = snap.get("report")
            # accept cached report only if non-empty string
            if rpt and isinstance(rpt, str) and rpt.strip():
                cached_report = rpt
                break
        except Exception:
            continue
    
    # Use cached report or current report
    report_to_send = cached_report or state.get("report") or ""
    
    # Send the email
    result = email_service.send_report(report_to_send, to_addr)
    
    # Build the assistant reply
    tail = f" Report emailed to {to_addr}." if result.get("ok") else f" {result.get('message', 'Email failed.')}"
    final_msg = tail
    
    # Update state
    state["messages"].append({"role": "assistant", "content": final_msg})
    state["messages"] = state["messages"][-6:]
    state["email_state"] = result
    
    return state
