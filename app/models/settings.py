from datetime import datetime
from app import get_db


class Settings:
    collection_name = 'settings'

    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def get(cls, key, default=None):
        """Lấy một setting theo key"""
        doc = cls.get_collection().find_one({'key': key})
        if doc:
            return doc.get('value', default)
        return default

    @classmethod
    def set(cls, key, value, description=None):
        """Lưu một setting"""
        update_data = {
            'value': value,
            'updated_at': datetime.now()
        }
        if description:
            update_data['description'] = description

        cls.get_collection().update_one(
            {'key': key},
            {'$set': update_data},
            upsert=True
        )

    @classmethod
    def get_all(cls):
        """Lấy tất cả settings"""
        return list(cls.get_collection().find())

    @classmethod
    def get_defaults(cls):
        """Lấy tất cả default values cho session form"""
        return {
            'court_name': cls.get('default_court_name', 'Waystation NQA'),
            'court_location': cls.get('default_court_location', ''),
            'price_per_hour': cls.get('default_court_price_per_hour', 139000),
            'total_hours': cls.get('default_total_hours', 2),
            'start_time': cls.get('default_start_time', '14:40'),
            'end_time': cls.get('default_end_time', '16:45'),
            'shuttlecock_price': cls.get('default_shuttlecock_price', 25000),
            'shuttlecock_quantity': cls.get('default_shuttlecock_quantity', 5),
        }

    @classmethod
    def ensure_defaults_exist(cls):
        """Đảm bảo các default settings tồn tại trong database"""
        defaults = [
            ('default_court_name', 'Waystation NQA', 'Tên sân mặc định'),
            ('default_court_location', '', 'Địa chỉ sân mặc định'),
            ('default_court_price_per_hour', 139000, 'Giá sân mặc định (VNĐ/giờ)'),
            ('default_total_hours', 2, 'Số giờ chơi mặc định'),
            ('default_start_time', '14:40', 'Giờ bắt đầu mặc định'),
            ('default_end_time', '16:45', 'Giờ kết thúc mặc định'),
            ('default_shuttlecock_price', 25000, 'Giá cầu mặc định (VNĐ/quả)'),
            ('default_shuttlecock_quantity', 3, 'Số quả cầu mặc định'),
        ]

        for key, value, description in defaults:
            existing = cls.get_collection().find_one({'key': key})
            if not existing:
                cls.get_collection().insert_one({
                    'key': key,
                    'value': value,
                    'description': description,
                    'updated_at': datetime.now()
                })
                print(f"[Settings] Created: {key} = {value}")