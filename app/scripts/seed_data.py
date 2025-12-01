#!/usr/bin/env python3
"""
Seed sample data for Badminton Tracker
Run: python scripts/seed_data. py
"""

import os
import sys
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'badminton_tracker')


def seed_data():
    print(f"Connecting to MongoDB: {MONGODB_URI}")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    # ==========================================
    # Clear existing data
    # ==========================================
    print("Clearing existing data...")
    db.players.delete_many({})
    db.settings.delete_many({})

    # ==========================================
    # Create Players
    # ==========================================
    print("Creating players...")
    players_data = [
        {
            "_id": ObjectId(),
            "name": "Tuấn",
            "phone": "0904035003",
            "email": "tuan@hopthudientu.com",
            "is_active": True,
            "is_default_court_payer": True,
            "is_default_shuttlecock_payer": False,
            "is_admin": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Mạnh",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": True,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Ly",
            "phone": "0901234567",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Nguyên",
            "phone": "0359532839",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Tiên",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Phát",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Tiến",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Trúc",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Giang",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Nguyễn",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Quốc",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "_id": ObjectId(),
            "name": "Khuê",
            "phone": "",
            "email": "",
            "is_active": True,
            "is_default_court_payer": False,
            "is_default_shuttlecock_payer": False,
            "is_admin": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ]

    db.players.insert_many(players_data)
    print(f"Created {len(players_data)} players")

    # Create player lookup
    p = {player["name"]: player["_id"] for player in players_data}

    # ==========================================
    # Create Settings
    # ==========================================
    print("Creating settings...")
    settings_data = [
        {
            "key": "default_court_payer",
            "value": {"player_id": p["Tuấn"], "player_name": "Tuấn"},
            "description": "Người mặc định trả tiền sân",
            "updated_at": datetime.now()
        },
        {
            "key": "default_shuttlecock_payer",
            "value": {"player_id": p["Mạnh"], "player_name": "Mạnh"},
            "description": "Người mặc định trả tiền cầu",
            "updated_at": datetime.now()
        },
        {
            "key": "default_court_price_per_hour",
            "value": 139000,
            "description": "Giá sân mặc định (VNĐ/giờ)",
            "updated_at": datetime.now()
        },
        {
            "key": "default_shuttlecock_price",
            "value": 25000,
            "description": "Giá cầu mặc định (VNĐ/quả)",
            "updated_at": datetime.now()
        }
    ]
    db.settings.insert_many(settings_data)
    print(f"Created {len(settings_data)} settings")


    # ==========================================
    # Summary
    # ==========================================
    print("\n" + "=" * 50)
    print("📊 DATABASE SUMMARY")
    print("=" * 50)
    print(f"\n👥 Players: {db.players.count_documents({})}")
    print(f"⚙️  Settings: {db. settings.count_documents({})}")

    print("\n✅ Seed data completed!")
    client.close()


if __name__ == '__main__':
    seed_data()