from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.models.player import Player
from app.models.session import Session
from app.models.transaction import Transaction

api_bp = Blueprint('api', __name__)


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_doc(value)
            elif isinstance(value, list):
                result[key] = serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc


# ==========================================
# Players API
# ==========================================

@api_bp.route('/players', methods=['GET'])
def get_players():
    players = Player.find_all()
    return jsonify(serialize_doc(players))


@api_bp.route('/players/<player_id>', methods=['GET'])
def get_player(player_id):
    player = Player.find_by_id(player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    return jsonify(serialize_doc(player))


@api_bp.route('/players', methods=['POST'])
def create_player():
    data = request.json
    player = Player. create(data)
    return jsonify(serialize_doc(player. to_dict())), 201


@api_bp.route('/players/<player_id>', methods=['PUT'])
def update_player(player_id):
    data = request.json
    Player.update(player_id, data)
    return jsonify({'message': 'Player updated'})


@api_bp.route('/players/<player_id>', methods=['DELETE'])
def delete_player(player_id):
    Player.delete(player_id)
    return jsonify({'message': 'Player deleted'})


# ==========================================
# Sessions API
# ==========================================

@api_bp.route('/sessions', methods=['GET'])
def get_sessions():
    start_date = request. args.get('start_date')
    end_date = request.args.get('end_date')
    player = request. args.get('player')

    if start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        if player:
            sessions = Session.find_by_player(player, start, end)
        else:
            sessions = Session. find_by_date_range(start, end)
    elif player:
        sessions = Session.find_by_player(player)
    else:
        sessions = Session.find_all()

    return jsonify(serialize_doc(sessions))


@api_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    session = Session.find_by_id(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(serialize_doc(session))


@api_bp. route('/sessions/<session_id>/payment', methods=['PUT'])
def update_payment(session_id):
    data = request.json
    player_name = data['player_name']
    amount_paid = data['amount_paid']

    success = Session.update_participant_payment(session_id, player_name, amount_paid)
    if not success:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({'message': 'Payment updated'})


# ==========================================
# Statistics API
# ==========================================

@api_bp.route('/stats/debts', methods=['GET'])
def get_debts():
    start_date = request. args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        debts = Session.get_all_debts(start, end)
    else:
        debts = Session.get_all_debts()

    return jsonify(serialize_doc(debts))


@api_bp.route('/stats/player/<player_name>', methods=['GET'])
def get_player_stats(player_name):
    start_date = request. args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date and end_date:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        stats = Session.get_player_debt(player_name, start, end)
    else:
        stats = Session.get_player_debt(player_name)

    if not stats:
        return jsonify({'message': 'No data found', 'total_owed': 0}), 200

    return jsonify(serialize_doc(stats))


@api_bp.route('/stats/monthly', methods=['GET'])
def get_monthly_stats():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    summary = Session.get_monthly_summary(year, month)
    return jsonify(serialize_doc(summary))


# ==========================================
# Payment Status API (for webhook polling)
# ==========================================

@api_bp.route('/payment-status/<player_name>', methods=['GET'])
def check_payment_status(player_name):
    """
    Check if there's a recent successful payment for this player.
    Frontend will poll this endpoint after showing QR code.
    Returns recent transactions within the last 5 minutes.
    """
    minutes = request.args.get('minutes', 5, type=int)

    # Find recent successful transactions for this player
    transactions = Transaction.find_recent_by_player(player_name, minutes=minutes)

    if transactions:
        # Get the most recent transaction
        latest = transactions[0]
        return jsonify({
            'success': True,
            'has_payment': True,
            'transaction': {
                'id': str(latest['_id']),
                'amount': latest.get('transfer_amount', 0),
                'content': latest.get('content', ''),
                'gateway': latest.get('gateway', ''),
                'created_at': latest.get('created_at').isoformat() if latest.get('created_at') else None,
                'sessions_updated': latest.get('sessions_updated', [])
            }
        })

    return jsonify({
        'success': True,
        'has_payment': False,
        'message': f'No recent payments found for {player_name}'
    })