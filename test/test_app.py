#!/usr/bin/env python3
"""Test Flask app startup"""

import os
from dotenv import load_dotenv

# Load .  env
load_dotenv()

print("=" * 50)
print("Environment Variables:")
print("=" * 50)
print(f"MONGODB_URI: '{os.getenv('MONGODB_URI')}'")
print(f"MONGODB_DB: '{os. getenv('MONGODB_DB')}'")
print(f"SECRET_KEY: '{os.getenv('SECRET_KEY', 'not set')[:20]}.. .'")
print("=" * 50)

# Test MongoDB connection
from pymongo import MongoClient

uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
print(f"\nConnecting to: {uri}")

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ MongoDB connection OK!")
    client.close()
except Exception as e:
    print(f"❌ MongoDB error: {e}")

# Test Flask app
print("\n" + "=" * 50)
print("Starting Flask app...")
print("=" * 50)

try:
    from app import create_app
    app = create_app()
    print("✅ Flask app created successfully!")
except Exception as e:
    print(f"❌ Flask app error: {e}")
    import traceback
    traceback.print_exc()