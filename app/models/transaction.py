from datetime import datetime, timedelta
from bson import ObjectId
from app import get_db


class Transaction:
    """Lưu lịch sử giao dịch từ Sepay webhook"""
    collection_name = 'transactions'

    def __init__(self, sepay_id, gateway, transaction_date, account_number,
                 content, transfer_amount, reference_code, player_name=None,
                 sessions_updated=None, status='pending', _id=None,
                 created_at=None):
        self._id = _id or ObjectId()
        self.sepay_id = sepay_id
        self.gateway = gateway
        self.transaction_date = transaction_date
        self.account_number = account_number
        self.content = content
        self.transfer_amount = transfer_amount
        self.reference_code = reference_code
        self.player_name = player_name
        self.sessions_updated = sessions_updated or []
        self.status = status  # success/failed/duplicate
        self.created_at = created_at or datetime.now()

    def to_dict(self):
        return {
            '_id': self._id,
            'sepay_id': self.sepay_id,
            'gateway': self.gateway,
            'transaction_date': self.transaction_date,
            'account_number': self.account_number,
            'content': self.content,
            'transfer_amount': self.transfer_amount,
            'reference_code': self.reference_code,
            'player_name': self.player_name,
            'sessions_updated': self.sessions_updated,
            'status': self.status,
            'created_at': self.created_at
        }

    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def find_by_sepay_id(cls, sepay_id):
        """Check if transaction already exists by sepay_id"""
        return cls.get_collection().find_one({'sepay_id': sepay_id})

    @classmethod
    def find_by_reference_code(cls, reference_code):
        """Check if transaction already exists by reference_code"""
        return cls.get_collection().find_one({'reference_code': reference_code})

    @classmethod
    def find_recent_by_player(cls, player_name, minutes=5):
        """Find recent transactions for a player within the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return list(cls.get_collection().find({
            'player_name': {'$regex': f'^{player_name}$', '$options': 'i'},
            'created_at': {'$gte': cutoff},
            'status': 'success'
        }).sort('created_at', -1))

    @classmethod
    def find_all(cls, limit=50):
        """Find all transactions"""
        return list(cls.get_collection().find().sort('created_at', -1).limit(limit))

    @classmethod
    def create(cls, data):
        """Create a new transaction"""
        transaction = cls(
            sepay_id=data['sepay_id'],
            gateway=data.get('gateway', ''),
            transaction_date=data.get('transaction_date'),
            account_number=data.get('account_number', ''),
            content=data.get('content', ''),
            transfer_amount=data.get('transfer_amount', 0),
            reference_code=data.get('reference_code', ''),
            player_name=data.get('player_name'),
            sessions_updated=data.get('sessions_updated', []),
            status=data.get('status', 'pending')
        )
        cls.get_collection().insert_one(transaction.to_dict())
        return transaction

    def save(self):
        """Save/update transaction"""
        self.get_collection().update_one(
            {'_id': self._id},
            {'$set': self.to_dict()},
            upsert=True
        )
        return self
