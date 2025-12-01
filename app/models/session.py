from datetime import datetime
from bson import ObjectId
from app import get_db


class Session:
    collection_name = 'sessions'

    def __init__(self, date, court, shuttlecock, participants,
                 start_time=None, end_time=None, status='pending',
                 note=None, created_by=None, _id=None,
                 created_at=None, updated_at=None):
        self._id = _id or ObjectId()
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.court = court
        self.shuttlecock = shuttlecock
        self.total_cost = court.get('total_court_price', 0) + shuttlecock.get('total_shuttlecock_price', 0)
        self.participants = participants
        self.status = status
        self.note = note
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self):
        return {
            '_id': self._id,
            'date': self.date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'court': self.court,
            'shuttlecock': self.shuttlecock,
            'total_cost': self.total_cost,
            'participants': self.participants,
            'status': self.status,
            'note': self.note,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def get_collection(cls):
        return get_db()[cls.collection_name]

    @classmethod
    def find_all(cls, limit=50):
        return list(cls.get_collection().find().sort('date', -1).limit(limit))

    @classmethod
    def find_by_id(cls, session_id):
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)
        return cls.get_collection().find_one({'_id': session_id})

    @classmethod
    def find_by_date_range(cls, start_date, end_date):
        return list(cls.get_collection().find({
            'date': {'$gte': start_date, '$lt': end_date}
        }).sort('date', -1))

    @classmethod
    def find_by_player(cls, player_name, start_date=None, end_date=None):
        query = {'participants.player_name': {'$regex': f'^{player_name}$', '$options': 'i'}}
        if start_date and end_date:
            query['date'] = {'$gte': start_date, '$lt': end_date}
        return list(cls.get_collection().find(query).sort('date', -1))

    # ==========================================
    # Debt calculations
    # ==========================================

    @classmethod
    def get_player_debt(cls, player_name, start_date=None, end_date=None):
        """Tính nợ của một người"""
        if start_date and end_date:
            sessions = cls.find_by_date_range(start_date, end_date)
        else:
            sessions = cls.find_all(limit=500)

        total_due = 0
        total_paid = 0
        total_to_receive = 0
        sessions_count = 0

        for session in sessions:
            for p in session.get('participants', []):
                if p.get('player_name', '').lower() == player_name.lower():
                    total_due += p.get('amount_due', 0)
                    total_paid += p.get('amount_paid', 0)
                    total_to_receive += p.get('amount_to_receive', 0)
                    sessions_count += 1

        if sessions_count == 0:
            return None

        return {
            '_id': player_name,
            'total_due': total_due,
            'total_paid': total_paid,
            'total_owed': max(0, total_due - total_paid - total_to_receive),
            'total_to_receive': total_to_receive,
            'sessions_count': sessions_count
        }

    @classmethod
    def get_all_debts(cls, start_date=None, end_date=None):
        """Lấy danh sách tất cả Người còn chưa thanh toán"""
        if start_date and end_date:
            sessions = cls.find_by_date_range(start_date, end_date)
        else:
            sessions = cls.find_all(limit=500)

        debts = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_due = p.get('amount_due', 0)
                amount_paid = p.get('amount_paid', 0)
                amount_to_receive = p.get('amount_to_receive', 0)

                # Chỉ tính nợ nếu không phải người được nhận lại tiền
                if amount_to_receive > 0:
                    continue

                owed = amount_due - amount_paid

                if owed > 0:
                    if player_name not in debts:
                        debts[player_name] = {
                            '_id': player_name,
                            'total_owed': 0,
                            'sessions_count': 0
                        }
                    debts[player_name]['total_owed'] += owed
                    debts[player_name]['sessions_count'] += 1

        result = list(debts.values())
        result.sort(key=lambda x: x['total_owed'], reverse=True)
        return result

    @classmethod
    def get_all_to_receive(cls, start_date=None, end_date=None):
        """Lấy danh sách tất cả người được nhận lại tiền"""
        if start_date and end_date:
            sessions = cls.find_by_date_range(start_date, end_date)
        else:
            sessions = cls.find_all(limit=500)

        to_receive = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_to_receive = p.get('amount_to_receive', 0)

                if amount_to_receive > 0:
                    if player_name not in to_receive:
                        to_receive[player_name] = {
                            '_id': player_name,
                            'total_to_receive': 0,
                            'sessions_count': 0
                        }
                    to_receive[player_name]['total_to_receive'] += amount_to_receive
                    to_receive[player_name]['sessions_count'] += 1

        result = list(to_receive.values())
        result.sort(key=lambda x: x['total_to_receive'], reverse=True)
        return result

    @classmethod
    def get_all_debts_all_time(cls):
        """Lấy tổng nợ tất cả thời gian"""
        return cls.get_all_debts(start_date=None, end_date=None)

    @classmethod
    def get_all_to_receive_all_time(cls):
        """Lấy tổng tiền cần trả lại tất cả thời gian"""
        return cls.get_all_to_receive(start_date=None, end_date=None)

    @classmethod
    def get_total_owed_all_time(cls):
        """Lấy tổng số tiền còn nợ all time"""
        debts = cls.get_all_debts_all_time()
        total_owed = sum(d['total_owed'] for d in debts)
        people_count = len(debts)

        return {
            'total_owed': total_owed,
            'people_count': people_count
        }

    @classmethod
    def get_total_to_receive_all_time(cls):
        """Lấy tổng số tiền cần trả lại all time"""
        to_receive = cls.get_all_to_receive_all_time()
        total = sum(d['total_to_receive'] for d in to_receive)
        people_count = len(to_receive)

        return {
            'total_to_receive': total,
            'people_count': people_count
        }

    @classmethod
    def get_all_debts_with_details(cls):
        """Lấy chi tiết nợ từng người với danh sách sessions"""
        sessions = cls.find_all(limit=500)

        debt_details = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_due = p.get('amount_due', 0)
                amount_paid = p.get('amount_paid', 0)
                amount_to_receive = p.get('amount_to_receive', 0)

                # Skip người được nhận lại tiền
                if amount_to_receive > 0:
                    continue

                owed = amount_due - amount_paid

                if owed > 0:
                    if player_name not in debt_details:
                        debt_details[player_name] = {
                            'total_owed': 0,
                            'sessions': []
                        }
                    debt_details[player_name]['total_owed'] += owed
                    debt_details[player_name]['sessions'].append({
                        'session_id': str(session['_id']),
                        'date': session['date'],
                        'amount_due': amount_due,
                        'amount_paid': amount_paid,
                        'owed': owed
                    })

        # Sort sessions by date
        for player_name in debt_details:
            debt_details[player_name]['sessions'].sort(
                key=lambda x: x['date'],
                reverse=True
            )

        return debt_details

    @classmethod
    def get_all_to_receive_with_details(cls):
        """Lấy chi tiết tiền cần trả lại từng người"""
        sessions = cls.find_all(limit=500)

        receive_details = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_to_receive = p.get('amount_to_receive', 0)
                amount_pre_paid = p.get('amount_pre_paid', 0)

                if amount_to_receive > 0:
                    if player_name not in receive_details:
                        receive_details[player_name] = {
                            'total_to_receive': 0,
                            'sessions': []
                        }
                    receive_details[player_name]['total_to_receive'] += amount_to_receive
                    receive_details[player_name]['sessions'].append({
                        'session_id': str(session['_id']),
                        'date': session['date'],
                        'amount_pre_paid': amount_pre_paid,
                        'amount_to_receive': amount_to_receive,
                        'note': p.get('note', '')
                    })

        # Sort sessions by date
        for player_name in receive_details:
            receive_details[player_name]['sessions'].sort(
                key=lambda x: x['date'],
                reverse=True
            )

        return receive_details

    @classmethod
    def get_debts_with_details_by_month(cls, year, month):
        """Lấy chi tiết nợ theo tháng cụ thể"""
        from dateutil.relativedelta import relativedelta
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1)

        sessions = cls.find_by_date_range(start_date, end_date)

        debt_details = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_due = p.get('amount_due', 0)
                amount_paid = p.get('amount_paid', 0)
                amount_to_receive = p.get('amount_to_receive', 0)

                if amount_to_receive > 0:
                    continue

                owed = amount_due - amount_paid

                if owed > 0:
                    if player_name not in debt_details:
                        debt_details[player_name] = {
                            'total_owed': 0,
                            'sessions': []
                        }
                    debt_details[player_name]['total_owed'] += owed
                    debt_details[player_name]['sessions'].append({
                        'session_id': str(session['_id']),
                        'date': session['date'],
                        'amount_due': amount_due,
                        'amount_paid': amount_paid,
                        'owed': owed
                    })

        for player_name in debt_details:
            debt_details[player_name]['sessions'].sort(
                key=lambda x: x['date'],
                reverse=True
            )

        return debt_details

    # ==========================================
    # Navigation helpers
    # ==========================================

    @classmethod
    def get_available_months(cls):
        """Lấy danh sách các tháng có session"""
        pipeline = [
            {'$group': {
                '_id': {
                    'year': {'$year': '$date'},
                    'month': {'$month': '$date'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': -1, '_id. month': -1}},
            {'$limit': 12}
        ]

        result = list(cls.get_collection().aggregate(pipeline))

        months = []
        for r in result:
            months.append({
                'year': r['_id']['year'],
                'month': r['_id']['month'],
                'count': r['count'],
                'label': f"Tháng {r['_id']['month']}/{r['_id']['year']}"
            })

        return months

    @classmethod
    def get_months_with_debts(cls):
        """Lấy danh sách các tháng có nợ chưa thanh toán"""
        sessions = cls.find_all(limit=500)

        months = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            session_date = session.get('date')
            if not session_date:
                continue

            year = session_date.year
            month = session_date.month
            key = f"{year}-{month}"

            for p in session.get('participants', []):
                amount_due = p.get('amount_due', 0)
                amount_paid = p.get('amount_paid', 0)
                amount_to_receive = p.get('amount_to_receive', 0)

                if amount_to_receive > 0:
                    continue

                owed = amount_due - amount_paid

                if owed > 0:
                    if key not in months:
                        months[key] = {
                            'year': year,
                            'month': month,
                            'total_owed': 0,
                            'people': set(),
                            'label': f"Tháng {month}/{year}"
                        }
                    months[key]['total_owed'] += owed
                    months[key]['people'].add(p.get('player_name', ''))

        result = []
        for key in sorted(months.keys(), reverse=True):
            m = months[key]
            result.append({
                'year': m['year'],
                'month': m['month'],
                'total_owed': m['total_owed'],
                'people_count': len(m['people']),
                'label': m['label']
            })

        return result

    # ==========================================
    # Monthly summary
    # ==========================================

    @classmethod
    def get_monthly_summary(cls, year, month):
        from dateutil.relativedelta import relativedelta
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1)

        sessions = cls.find_by_date_range(start_date, end_date)
        debts = cls.get_all_debts(start_date, end_date)
        to_receive = cls.get_all_to_receive(start_date, end_date)

        total_cost = sum(s.get('total_cost', 0) for s in sessions)
        total_court = sum(s.get('court', {}).get('total_court_price', 0) for s in sessions)
        total_shuttlecock = sum(s.get('shuttlecock', {}).get('total_shuttlecock_price', 0) for s in sessions)
        total_owed = sum(d['total_owed'] for d in debts)
        total_to_receive = sum(r['total_to_receive'] for r in to_receive)

        return {
            'year': year,
            'month': month,
            'sessions_count': len(sessions),
            'total_cost': total_cost,
            'total_court': total_court,
            'total_shuttlecock': total_shuttlecock,
            'total_owed': total_owed,
            'total_to_receive': total_to_receive,
            'debts': debts,
            'to_receive': to_receive,
            'sessions': sessions
        }

    # ==========================================
    # CRUD operations
    # ==========================================

    @classmethod
    def create(cls, data):
        session = cls(
            date=data['date'],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            court=data['court'],
            shuttlecock=data['shuttlecock'],
            participants=data['participants'],
            status=data.get('status', 'completed'),
            note=data.get('note'),
            created_by=data.get('created_by')
        )
        cls.get_collection().insert_one(session.to_dict())
        return session

    @classmethod
    def update(cls, session_id, data):
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)
        data['updated_at'] = datetime.now()
        cls.get_collection().update_one(
            {'_id': session_id},
            {'$set': data}
        )

    @classmethod
    def delete(cls, session_id):
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)
        cls.get_collection().delete_one({'_id': session_id})

    @classmethod
    def update_participant_payment(cls, session_id, player_name, amount_paid):
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)

        session = cls.find_by_id(session_id)
        if not session:
            return False

        updated = False
        for p in session['participants']:
            if p.get('player_name', '').lower() == player_name.lower():
                p['amount_paid'] = amount_paid
                p['is_paid'] = amount_paid >= p.get('amount_due', 0)
                if p['is_paid']:
                    p['paid_at'] = datetime.now()
                else:
                    p['paid_at'] = None
                updated = True
                break

        if updated:
            cls.get_collection().update_one(
                {'_id': session_id},
                {'$set': {
                    'participants': session['participants'],
                    'updated_at': datetime.now()
                }}
            )
        return updated

    @classmethod
    def update_participant_received(cls, session_id, player_name):
        """Đánh dấu đã trả lại tiền cho người chơi"""
        if isinstance(session_id, str):
            session_id = ObjectId(session_id)

        session = cls.find_by_id(session_id)
        if not session:
            return False

        updated = False
        for p in session['participants']:
            if p.get('player_name', '').lower() == player_name.lower() and p.get('amount_to_receive', 0) > 0:
                p['amount_returned'] = p.get('amount_to_receive', 0)
                p['amount_to_receive'] = 0
                p['returned_at'] = datetime.utcnow()
                p['note'] = (p.get('note', '') + ' - Đã trả lại').strip(' - ')
                updated = True
                break

        if updated:
            cls.get_collection().update_one(
                {'_id': session_id},
                {'$set': {
                    'participants': session['participants'],
                    'updated_at': datetime.utcnow()
                }}
            )
        return updated

    @classmethod
    def get_all_to_receive_with_details(cls):
        """Lấy chi tiết tiền cần trả lại từng người"""
        sessions = cls.find_all(limit=500)

        receive_details = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_to_receive = p.get('amount_to_receive', 0)
                amount_pre_paid = p.get('amount_pre_paid', 0)

                if amount_to_receive > 0:
                    if player_name not in receive_details:
                        receive_details[player_name] = {
                            'total_to_receive': 0,
                            'sessions': []
                        }
                    receive_details[player_name]['total_to_receive'] += amount_to_receive
                    receive_details[player_name]['sessions'].append({
                        'session_id': str(session['_id']),
                        'date': session['date'],
                        'amount_pre_paid': amount_pre_paid,
                        'amount_to_receive': amount_to_receive,
                        'note': p.get('note', '')
                    })

        # Sort sessions by date
        for player_name in receive_details:
            receive_details[player_name]['sessions'].sort(
                key=lambda x: x['date'],
                reverse=True
            )

        return receive_details

    @classmethod
    def get_to_receive_with_details_by_month(cls, year, month):
        """Lấy chi tiết tiền cần trả lại theo tháng cụ thể"""
        from dateutil.relativedelta import relativedelta
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1)

        sessions = cls.find_by_date_range(start_date, end_date)

        receive_details = {}

        for session in sessions:
            if session.get('status') != 'completed':
                continue

            for p in session.get('participants', []):
                player_name = p.get('player_name', '')
                amount_to_receive = p.get('amount_to_receive', 0)
                amount_pre_paid = p.get('amount_pre_paid', 0)

                if amount_to_receive > 0:
                    if player_name not in receive_details:
                        receive_details[player_name] = {
                            'total_to_receive': 0,
                            'sessions': []
                        }
                    receive_details[player_name]['total_to_receive'] += amount_to_receive
                    receive_details[player_name]['sessions'].append({
                        'session_id': str(session['_id']),
                        'date': session['date'],
                        'amount_pre_paid': amount_pre_paid,
                        'amount_to_receive': amount_to_receive,
                        'note': p.get('note', '')
                    })

        # Sort sessions by date
        for player_name in receive_details:
            receive_details[player_name]['sessions'].sort(
                key=lambda x: x['date'],
                reverse=True
            )

        return receive_details



    def save(self):
        self.updated_at = datetime.now()
        self.get_collection().update_one(
            {'_id': self._id},
            {'$set': self.to_dict()},
            upsert=True
        )
        return self
