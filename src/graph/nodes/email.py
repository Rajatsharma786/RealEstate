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
from datetime import datetime
from io import BytesIO
import textwrap
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import re
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
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, 
                            rightMargin=36, leftMargin=36,  # Reduced margins for more space
                            topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f77b4'),
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#34495e'),
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        # Build the story (content)
        story = []
        
        # Add header with logo area
        story.append(Paragraph("🏠 Real Estate Market Report", title_style))
        story.append(Spacer(1, 12))
        
        # Add date
        current_date = datetime.now().strftime("%B %d, %Y")
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7f8c8d'),
            fontName='Helvetica-Oblique'
        )
        story.append(Paragraph(f"Generated on {current_date}", date_style))
        story.append(Spacer(1, 20))
        
        # Process the report content
        lines = report.splitlines()
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                story.append(Spacer(1, 6))
                i += 1
                continue
                
            # Check for email body marker
            if line.startswith("**Email Body:**"):
                i += 1
                continue
                
            # Check for headings (### or ####)
            if line.startswith("### "):
                heading_text = line[4:].strip()
                story.append(Paragraph(heading_text, heading_style))
                i += 1
                continue
                
            elif line.startswith("#### "):
                subheading_text = line[5:].strip()
                story.append(Paragraph(subheading_text, subheading_style))
                i += 1
                continue
                
            # Check for tables (lines with |)
            elif "|" in line and not line.startswith("**"):
                # Collect table rows
                table_rows = []
                while i < len(lines) and "|" in lines[i]:
                    row_line = lines[i].strip()
                    if row_line.startswith("|") and row_line.endswith("|"):
                        # Clean up the row
                        cells = [cell.strip() for cell in row_line[1:-1].split("|")]
                        table_rows.append(cells)
                    i += 1
                
                if table_rows:
                    # Calculate available width (A4 width minus margins)
                    available_width = A4[0] - 72  # 72 points for left + right margins
                    
                    # Count columns
                    num_cols = len(table_rows[0]) if table_rows else 0
                    
                    # Calculate column widths based on content
                    col_widths = []
                    if num_cols > 0:
                        # Base width per column
                        base_width = available_width / num_cols
                        
                        # Adjust widths based on column content
                        for col_idx in range(num_cols):
                            max_content_length = 0
                            for row in table_rows:
                                if col_idx < len(row):
                                    content_length = len(str(row[col_idx]))
                                    max_content_length = max(max_content_length, content_length)
                            
                            # Set minimum and maximum widths
                            min_width = 60  # Minimum 60 points
                            max_width = available_width * 0.3  # Maximum 30% of page width
                            
                            # Calculate width based on content
                            content_width = max_content_length * 6  # Approximate 6 points per character
                            width = max(min_width, min(content_width, max_width))
                            col_widths.append(width)
                        
                        # Ensure total width doesn't exceed available space
                        total_width = sum(col_widths)
                        if total_width > available_width:
                            scale_factor = available_width / total_width
                            col_widths = [w * scale_factor for w in col_widths]
                    else:
                        col_widths = None
                    
                    # Create table with calculated widths
                    table = Table(table_rows, colWidths=col_widths)
                    
                    # Enhanced table styling
                    table.setStyle(TableStyle([
                        # Header row styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),  # Reduced font size
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        
                        # Data rows styling
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Smaller font for data
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                        ('TOPPADDING', (0, 1), (-1, -1), 4),
                        
                        # Grid and borders
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2980b9')),
                        
                        # Alternating row colors
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                        
                        # Text wrapping for long content
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    
                    # Add table to story
                    story.append(table)
                    story.append(Spacer(1, 12))
                continue
                
            # Check for bullet points
            elif line.startswith("- ") or line.startswith("* "):
                bullet_text = line[2:].strip()
                # Handle bold text in bullets
                bullet_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', bullet_text)
                story.append(Paragraph(f"• {bullet_text}", body_style))
                i += 1
                continue
                
            # Check for bold text
            elif line.startswith("**") and line.endswith("**"):
                bold_text = line[2:-2].strip()
                bold_style = ParagraphStyle(
                    'BoldStyle',
                    parent=body_style,
                    fontName='Helvetica-Bold',
                    fontSize=12
                )
                story.append(Paragraph(bold_text, bold_style))
                i += 1
                continue
                
            # Regular paragraph
            else:
                # Handle bold text in paragraphs
                paragraph_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                story.append(Paragraph(paragraph_text, body_style))
                i += 1
                continue
        
        # Add footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#95a5a6'),
            fontName='Helvetica-Oblique'
        )
        story.append(Paragraph("Generated by Real Estate AI Assistant", footer_style))
        story.append(Paragraph("For more insights, visit our platform", footer_style))
        
        # Build PDF
        doc.build(story)
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
