from datetime import datetime
from bson import ObjectId
from app import get_db


class Player:
    collection_name = 'players'

    def __init__(self, name, phone=None, email=None, is_active=True,
                 is_default_court_payer=False, is_default_shuttlecock_payer=False,
                 is_admin=False, _id=None, created_at=None, updated_at=None):
        self._id = _id or ObjectId()
        self.name = name
        self.phone = phone
        self.email = email
        self.is_active = is_active
        self.is_default_court_payer = is_default_court_payer
        self. is_default_shuttlecock_payer = is_default_shuttlecock_payer
        self. is_admin = is_admin
        self.created_at = created_at or datetime.now()
        self. updated_at = updated_at or datetime. now()

    def to_dict(self):
        return {
            '_id': self._id,
            'name': self. name,
            'phone': self.phone,
            'email': self.email,
            'is_active': self.is_active,
            'is_default_court_payer': self.is_default_court_payer,
            'is_default_shuttlecock_payer': self.is_default_shuttlecock_payer,
            'is_admin': self.is_admin,
            'created_at': self. created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(
            _id=data.get('_id'),
            name=data['name'],
            phone=data.get('phone'),
            email=data.get('email'),
            is_active=data. get('is_active', True),
            is_default_court_payer=data.get('is_default_court_payer', False),
            is_default_shuttlecock_payer=data.get('is_default_shuttlecock_payer', False),
            is_admin=data.get('is_admin', False),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def find_all(cls, active_only=True):
        query = {'is_active': True} if active_only else {}
        return list(cls.get_collection().find(query). sort('name', 1))

    @classmethod
    def find_by_id(cls, player_id):
        if isinstance(player_id, str):
            player_id = ObjectId(player_id)
        return cls. get_collection().find_one({'_id': player_id})

    @classmethod
    def find_by_name(cls, name):
        return cls.get_collection().find_one({
            'name': {'$regex': f'^{name}$', '$options': 'i'}
        })

    @classmethod
    def get_default_court_payer(cls):
        return cls.get_collection().find_one({'is_default_court_payer': True})

    @classmethod
    def get_default_shuttlecock_payer(cls):
        return cls.get_collection().find_one({'is_default_shuttlecock_payer': True})

    @classmethod
    def create(cls, data):
        player = cls(
            name=data['name'],
            phone=data.get('phone'),
            email=data.get('email'),
            is_default_court_payer=data.get('is_default_court_payer', False),
            is_default_shuttlecock_payer=data.get('is_default_shuttlecock_payer', False),
            is_admin=data.get('is_admin', False)
        )
        cls.get_collection(). insert_one(player.to_dict())
        return player

    @classmethod
    def update(cls, player_id, data):
        if isinstance(player_id, str):
            player_id = ObjectId(player_id)
        data['updated_at'] = datetime.now()
        cls.get_collection(). update_one(
            {'_id': player_id},
            {'$set': data}
        )

    @classmethod
    def delete(cls, player_id):
        if isinstance(player_id, str):
            player_id = ObjectId(player_id)
        cls.get_collection().update_one(
            {'_id': player_id},
            {'$set': {'is_active': False, 'updated_at': datetime. now()}}
        )

    def save(self):
        self.updated_at = datetime.now()
        self.get_collection().update_one(
            {'_id': self._id},
            {'$set': self.to_dict()},
            upsert=True
        )
        return self