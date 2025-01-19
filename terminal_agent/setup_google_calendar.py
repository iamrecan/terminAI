#!/usr/bin/env python3

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle
from dotenv import load_dotenv

def setup_google_calendar():
    """
    Helper script to set up Google Calendar authentication.
    """
    print("Google Calendar Setup Helper")
    print("-" * 50)
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("\n❌ credentials.json not found!")
        print("Please follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Calendar API")
        print("4. Go to APIs & Services > Credentials")
        print("5. Create OAuth 2.0 Client ID (Desktop application)")
        print("6. Download the client configuration")
        print("7. Save it as 'credentials.json' in this directory")
        return False

    print("✅ credentials.json found")
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None
    
    # Check if we have valid token
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            print("✅ Existing token found")

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("\n🔐 Starting OAuth2 authorization flow...")
            print("A browser window will open. Please log in and authorize the application.")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            print("💾 Saving new token...")
            pickle.dump(creds, token)
    
    print("\n✅ Google Calendar setup complete!")
    return True

if __name__ == '__main__':
    setup_google_calendar()
