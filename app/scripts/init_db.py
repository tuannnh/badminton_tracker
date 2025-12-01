#!/usr/bin/env python3
"""
Initialize MongoDB database with indexes
Run: python scripts/init_db. py
"""

import os
import sys
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path. abspath(__file__))))

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'badminton_tracker')


def init_database():
    print(f"Connecting to MongoDB: {MONGODB_URI}")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    print(f"Initializing database: {MONGODB_DB}")

    # ==========================================
    # Drop existing collections (để xóa validation cũ)
    # ==========================================
    print("Dropping existing collections...")
    for collection_name in ['players', 'sessions', 'users', 'settings']:
        if collection_name in db.list_collection_names():
            db. drop_collection(collection_name)
            print(f"   Dropped: {collection_name}")

    # ==========================================
    # Create collections WITHOUT strict validation
    # (Validation gây phức tạp, ta dùng application-level validation thay thế)
    # ==========================================
    print("Creating collections...")
    db.create_collection('players')
    db.create_collection('sessions')
    db.create_collection('users')
    db.create_collection('settings')

    # ==========================================
    # Create indexes
    # ==========================================
    print("Creating indexes...")

    # Players collection
    db.players.create_index([("name", ASCENDING)])
    db.players.create_index([("is_active", ASCENDING)])
    db.players.create_index([("is_default_court_payer", ASCENDING)])
    db.players.create_index([("is_default_shuttlecock_payer", ASCENDING)])
    print("   ✓ players indexes")

    # Sessions collection
    db.sessions.create_index([("date", DESCENDING)])
    db.sessions.create_index([("status", ASCENDING)])
    db.sessions.create_index([("participants. player_id", ASCENDING)])
    db.sessions.create_index([("participants. player_name", ASCENDING)])
    db.sessions.create_index([("participants. is_paid", ASCENDING)])
    db.sessions.create_index([
        ("date", DESCENDING),
        ("participants.player_name", ASCENDING)
    ])
    print("   ✓ sessions indexes")

    # Users collection
    db.users.create_index([("username", ASCENDING)], unique=True, sparse=True)
    db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
    print("   ✓ users indexes")

    # Settings collection
    db.settings.create_index([("key", ASCENDING)], unique=True)
    print("   ✓ settings indexes")

    print("\n✅ Database initialization completed!")
    print(f"Collections: {db.list_collection_names()}")

    client.close()


if __name__ == '__main__':
    init_database()