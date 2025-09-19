#!/usr/bin/env python3
"""
Live App Debug - Check if live app reaches email node
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

def debug_live_app_workflow():
    print("🔍 LIVE APP WORKFLOW DEBUG")
    print("=" * 50)
    print(f"Debug time: {datetime.now()}")
    print()
    
    try:
        from src.graph.workflow import app
        from src.services.db.sql import db_service
        
        # Get a test user
        users = db_service.get_all_users()
        if not users:
            print("❌ No users found")
            return
            
        test_user = users[0]
        print(f"Testing with user: {test_user['username']} ({test_user['email']})")
        print()
        
        # Test question
        question = "send me a property report"
        
        # Create state exactly like app.py
        initial_state = {
            "question": question,
            "context": [],
            "needs_sql": False,
            "sql_result": "",
            "llm_sql": "",
            "messages": [{"role": "user", "content": question}],
            "report": "",
            "needs_email": False,
            "email_state": None,
            "user_id": test_user['username']
        }
        
        print("🧪 Testing workflow with detailed event tracking:")
        print(f"   Question: {question}")
        print(f"   User ID: {test_user['username']}")
        print()
        
        # Use the same configuration as app.py
        conversation_id = f"debug_conv_{int(datetime.now().timestamp())}"
        events = app.stream(
            initial_state,
            {"configurable": {"thread_id": conversation_id}, "recursion_limit": 150},
            stream_mode="values"
        )
        
        print("📧 Processing workflow events:")
        print("-" * 40)
        
        email_node_reached = False
        email_sent = False
        final_email_state = None
        
        for i, event in enumerate(events):
            print(f"Event {i+1}:")
            
            # Check all relevant fields
            if "needs_email" in event:
                print(f"  needs_email: {event['needs_email']}")
            
            if "email_state" in event:
                if event["email_state"] is not None:
                    print(f"  email_state: {event['email_state']} (type: {type(event['email_state'])})")
                    if isinstance(event["email_state"], dict):
                        email_node_reached = True
                        final_email_state = event["email_state"]
                        email_sent = event["email_state"].get("ok", False)
                else:
                    print(f"  email_state: None")
            
            if "report" in event and event["report"]:
                print(f"  report: {len(event['report'])} chars")
            
            if "messages" in event:
                print(f"  messages: {len(event['messages'])} messages")
            
            print()
        
        print("🔍 FINAL ANALYSIS:")
        print("=" * 50)
        print(f"Email node reached: {email_node_reached}")
        print(f"Email sent: {email_sent}")
        print(f"Final email state: {final_email_state}")
        
        if email_node_reached and email_sent:
            print("✅ SUCCESS: Email node executed and email sent!")
            print("🎉 The workflow is working correctly")
            print()
            print("🔍 NEXT STEPS:")
            print("Since the test works but live app doesn't:")
            print("1. Check if live app is using different user_id")
            print("2. Check if live app is using cached results")
            print("3. Check if live app is interrupting the workflow")
            print("4. Add debug prints to live app to see what's happening")
        elif email_node_reached and not email_sent:
            print("❌ ISSUE: Email node reached but email failed")
            if final_email_state:
                print(f"Error: {final_email_state.get('message', 'Unknown error')}")
        else:
            print("❌ ISSUE: Email node was never reached!")
            print("This suggests the workflow is being interrupted before reaching the email node.")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_live_app_workflow()