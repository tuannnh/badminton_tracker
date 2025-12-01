from datetime import datetime
from bson import ObjectId
import bcrypt
from app import get_db


class User:
    collection_name = 'users'

    def __init__(self, username, email, password_hash, role='admin',
                 is_active=True, _id=None, created_at=None, updated_at=None):
        self._id = _id or ObjectId()
        self.username = username
        self. email = email
        self.password_hash = password_hash
        self.role = role
        self. is_active = is_active
        self.created_at = created_at or datetime.now()
        self. updated_at = updated_at or datetime. now()

    def to_dict(self):
        return {
            '_id': self._id,
            'username': self. username,
            'email': self.email,
            'password_hash': self. password_hash,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self. created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def hash_password(cls, password):
        """Hash password với bcrypt"""
        return bcrypt.hashpw(password. encode('utf-8'), bcrypt.gensalt()). decode('utf-8')

    @classmethod
    def check_password(cls, password, password_hash):
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    @classmethod
    def find_by_username(cls, username):
        """Tìm user theo username"""
        return cls.get_collection().find_one({'username': username, 'is_active': True})

    @classmethod
    def find_by_id(cls, user_id):
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return cls.get_collection(). find_one({'_id': user_id})

    @classmethod
    def authenticate(cls, username, password):
        """Xác thực user, trả về user doc nếu thành công"""
        user = cls.find_by_username(username)
        if user and cls.check_password(password, user['password_hash']):
            return user
        return None

    @classmethod
    def create(cls, username, email, password, role='admin'):
        """Tạo user mới"""
        user = cls(
            username=username,
            email=email,
            password_hash=cls.hash_password(password),
            role=role
        )
        cls.get_collection(). insert_one(user.to_dict())
        return user

    @classmethod
    def update_password(cls, user_id, new_password):
        """Cập nhật password"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        cls.get_collection(). update_one(
            {'_id': user_id},
            {'$set': {
                'password_hash': cls.hash_password(new_password),
                'updated_at': datetime.now()
            }}
        )

    @classmethod
    def ensure_admin_exists(cls):
        """Đảm bảo có ít nhất 1 admin account"""
        admin = cls.find_by_username('admin')
        if not admin:
            cls.create(
                username='admin',
                email='admin@badmintontracker.com',
                password='0112358',
                role='admin'
            )
            print("[User] Created default admin account: admin / 0112358")
            return True
        return False