#!/usr/bin/env python3
"""
GCP Email Debug - Check GCP-specific email issues
"""

import os
import sys
import requests
import smtplib
import socket
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

def check_gcp_email_issues():
    print("�� GCP EMAIL DEBUG")
    print("=" * 50)
    print(f"Check time: {datetime.now()}")
    print()
    
    try:
        # Check 1: GCP Environment Info
        print("🧪 CHECK 1: GCP Environment Info")
        print("-" * 40)
        
        # Check if running on GCP
        gcp_metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/"
        try:
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(gcp_metadata_url, headers=headers, timeout=5)
            if response.status_code == 200:
                print("✅ Running on GCP")
                
                # Get GCP instance info
                try:
                    zone_response = requests.get(gcp_metadata_url + "zone", headers=headers, timeout=5)
                    if zone_response.status_code == 200:
                        zone = zone_response.text.split('/')[-1]
                        print(f"   Zone: {zone}")
                except:
                    pass
                
                try:
                    machine_type_response = requests.get(gcp_metadata_url + "machine-type", headers=headers, timeout=5)
                    if machine_type_response.status_code == 200:
                        machine_type = machine_type_response.text.split('/')[-1]
                        print(f"   Machine Type: {machine_type}")
                except:
                    pass
                    
            else:
                print("❌ Not running on GCP or metadata not accessible")
        except:
            print("❌ Could not access GCP metadata")
        
        print()
        
        # Check 2: External IP and GCP IP ranges
        print("🧪 CHECK 2: IP Address and GCP IP Ranges")
        print("-" * 40)
        
        try:
            # Get external IP
            ip_response = requests.get('https://api.ipify.org?format=json', timeout=10)
            if ip_response.status_code == 200:
                external_ip = ip_response.json()['ip']
                print(f"✅ External IP: {external_ip}")
                
                # Check if it's a GCP IP
                gcp_ip_ranges = [
                    "35.190.247.0/24", "64.233.160.0/19", "66.102.0.0/20",
                    "66.249.80.0/20", "72.14.192.0/18", "74.125.0.0/16",
                    "108.177.8.0/21", "173.194.0.0/16", "209.85.128.0/17"
                ]
                
                print("🌐 GCP IP ranges (partial list):")
                for ip_range in gcp_ip_ranges[:3]:
                    print(f"   {ip_range}")
                print("   ... (GCP has many IP ranges)")
                
                print(f"🌐 Check IP reputation at: https://www.abuseipdb.com/check/{external_ip}")
                
            else:
                print("❌ Could not get external IP")
        except Exception as e:
            print(f"❌ IP check failed: {str(e)}")
        
        print()
        
        # Check 3: GCP-specific SMTP issues
        print("🧪 CHECK 3: GCP SMTP Connection Test")
        print("-" * 40)
        
        from src.graph.nodes.email import EmailService
        email_service = EmailService()
        
        print(f"SMTP Server: {email_service.smtp_server}:{email_service.smtp_port}")
        print(f"Sender: {email_service.sender_email}")
        print()
        
        try:
            # Test SMTP connection
            print("Connecting to Gmail SMTP...")
            server = smtplib.SMTP(email_service.smtp_server, email_service.smtp_port)
            server.set_debuglevel(1)  # Enable verbose logging
            
            print("Starting TLS...")
            server.starttls()
            
            print("Authenticating...")
            server.login(email_service.sender_email, email_service.sender_password)
            
            print("✅ SMTP connection successful")
            
            # Send a test email
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = email_service.sender_email
            msg['To'] = "tonystark0101786@gmail.com"
            msg['Subject'] = f"GCP Email Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            body = f"""
            Test email from GCP server
            
            Timestamp: {datetime.now()}
            External IP: {external_ip if 'external_ip' in locals() else 'Unknown'}
            Platform: Google Cloud Platform
            
            This is a test to check if Gmail is blocking emails from this GCP server.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            print("Sending test email...")
            server.send_message(msg)
            server.quit()
            
            print("✅ Test email sent successfully")
            print("📧 Check your email in 1-2 minutes")
            
        except Exception as e:
            print(f"❌ SMTP Error: {str(e)}")
            print("   This might indicate Gmail is blocking GCP IPs")
        
        print()
        
        # Check 4: GCP-specific recommendations
        print("🧪 CHECK 4: GCP-Specific Recommendations")
        print("-" * 40)
        
        print("GCP email delivery issues:")
        print("1. GCP IPs might be flagged by Gmail")
        print("2. GCP has strict outbound email policies")
        print("3. Consider using GCP's SendGrid or Mailgun")
        print("4. Check GCP firewall rules for outbound SMTP")
        print()
        
        print("Solutions:")
        print("1. Use GCP's SendGrid add-on")
        print("2. Use GCP's Mailgun add-on")
        print("3. Use GCP's Cloud Functions with SendGrid")
        print("4. Check GCP firewall rules")
        print("5. Use a different email service")
        
    except Exception as e:
        print(f"❌ GCP debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_gcp_email_issues()