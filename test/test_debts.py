#!/usr/bin/env python3
"""Test debt queries"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os. getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os. getenv('MONGODB_DB', 'badminton_tracker')

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

print("=" * 50)
print("DEBUG: Checking database")
print("=" * 50)

# 1. Check sessions
sessions = list(db.sessions. find())
print(f"\n📅 Total sessions: {len(sessions)}")

for s in sessions:
    print(f"\n--- Session: {s['date']. strftime('%d/%m/%Y')} ---")
    print(f"Total cost: {s['total_cost']:,}đ")
    print("Participants:")
    for p in s['participants']:
        owed = p['amount_due'] - p['amount_paid']
        status = "✅ Paid" if p['is_paid'] else f"❌ Owes {owed:,}đ"
        print(f"  - {p['player_name']}: due={p['amount_due']:,}, paid={p['amount_paid']:,}, is_paid={p['is_paid']} -> {status}")

# 2. Test aggregation query
print("\n" + "=" * 50)
print("DEBUG: Testing aggregation query")
print("=" * 50)

pipeline = [
    {'$match': {'status': 'completed'}},
    {'$unwind': '$participants'},
    {'$match': {'participants.is_paid': False}},
    {'$group': {
        '_id': '$participants.player_name',
        'total_owed': {
            '$sum': {'$subtract': ['$participants.amount_due', '$participants.amount_paid']}
        },
        'sessions_count': {'$sum': 1}
    }},
    {'$match': {'total_owed': {'$gt': 0}}},
    {'$sort': {'total_owed': -1}}
]

debts = list(db.sessions.aggregate(pipeline))
print(f"\nDebts found: {len(debts)}")
for d in debts:
    print(f"  - {d['_id']}: {d['total_owed']:,}đ ({d['sessions_count']} sessions)")

# 3. Check raw data
print("\n" + "=" * 50)
print("DEBUG: Raw unpaid participants")
print("=" * 50)

for s in sessions:
    for p in s['participants']:
        if not p['is_paid']:
            owed = p['amount_due'] - p['amount_paid']
            print(f"  - {s['date'].strftime('%d/%m/%Y')} | {p['player_name']}: owes {owed:,}đ")

client.close()