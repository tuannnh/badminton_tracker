import re
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.models.transaction import Transaction
from app.models.session import Session
from app.models.player import Player

webhook_bp = Blueprint('webhook', __name__)

# Keywords to detect valid badminton payments (case-insensitive)
PAYMENT_KEYWORDS = ['cau long', 'caulong', 'badminton', 'cl']


def extract_player_short_code(content):
    """
    Parse player short_code from transaction content.
    Find pattern P + 3 digits (P001, P002, ...)
    Returns the Player document if found, else None.
    """
    if not content:
        return None

    # Find pattern P followed by 3 digits
    match = re.search(r'P(\d{3})', content.upper())
    if match:
        short_code = "P" + match.group(1)
        player = Player.find_by_short_code(short_code)
        return player
    return None


def extract_player_name(content):
    """
    Parse player name from transaction content.
    Extract the part before the keyword.
    Example: "Manh thanh toan cau long" → "Manh"
    """
    if not content:
        return None

    content_lower = content.lower()

    # Find the keyword and extract text before it
    for keyword in PAYMENT_KEYWORDS:
        pos = content_lower.find(keyword)
        if pos > 0:
            # Get text before keyword
            before_keyword = content[:pos].strip()
            # Clean up common payment phrases
            # Remove common Vietnamese payment phrases
            phrases_to_remove = [
                'thanh toan', 'tt', 'chuyen tien', 'tra tien',
                'gui tien', 'nop tien', 'dong tien'
            ]
            name = before_keyword
            for phrase in phrases_to_remove:
                name = re.sub(
                    rf'\b{phrase}\b',
                    '',
                    name,
                    flags=re.IGNORECASE
                ).strip()

            # Clean up extra spaces
            name = ' '.join(name.split())

            if name:
                return name

    return None


def is_valid_payment_content(content):
    """Check if content contains valid payment keywords"""
    if not content:
        return False
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in PAYMENT_KEYWORDS)


def validate_api_key(api_key_header):
    """Validate Sepay API key from header"""
    configured_key = current_app.config.get('SEPAY_API_KEY', '')
    if not configured_key:
        # If no API key configured, allow all requests
        return True
    return api_key_header == configured_key


@webhook_bp.route('/sepay', methods=['POST'])
def sepay_webhook():
    """
    Webhook endpoint for Sepay to call when there's a new transaction.

    Expected payload:
    {
        "id": 92704,
        "gateway": "TPBank",
        "transactionDate": "2023-03-25 14:02:37",
        "accountNumber": "03365790401",
        "code": null,
        "content": "Manh thanh toan cau long",
        "transferType": "in",
        "transferAmount": 50000,
        "accumulated": 19077000,
        "subAccount": null,
        "referenceCode": "FT23084xxxxxx",
        "description": ""
    }
    """
    # Validate API key
    api_key = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not api_key:
        api_key = request.headers.get('X-API-Key', '')

    if not validate_api_key(api_key):
        return jsonify({'success': False, 'message': 'Invalid API key'}), 401

    # Parse request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    sepay_id = data.get('id')
    transfer_type = data.get('transferType')
    content = data.get('content', '')
    transfer_amount = data.get('transferAmount', 0)
    reference_code = data.get('referenceCode', '')
    gateway = data.get('gateway', '')
    account_number = data.get('accountNumber', '')
    transaction_date_str = data.get('transactionDate', '')

    # Parse transaction date
    transaction_date = None
    if transaction_date_str:
        try:
            transaction_date = datetime.strptime(
                transaction_date_str, '%Y-%m-%d %H:%M:%S'
            )
        except ValueError:
            transaction_date = datetime.now()

    # Check for duplicate transaction
    if sepay_id:
        existing = Transaction.find_by_sepay_id(sepay_id)
        if existing:
            return jsonify({
                'success': False,
                'message': 'Duplicate transaction',
                'transaction_id': str(existing['_id'])
            }), 200

    # Only process incoming transfers
    if transfer_type != 'in':
        Transaction.create({
            'sepay_id': sepay_id,
            'gateway': gateway,
            'transaction_date': transaction_date,
            'account_number': account_number,
            'content': content,
            'transfer_amount': transfer_amount,
            'reference_code': reference_code,
            'status': 'failed',
            'player_name': None,
            'sessions_updated': []
        })
        return jsonify({
            'success': False,
            'message': 'Not an incoming transfer'
        }), 200

    # Check if content contains valid payment keywords
    if not is_valid_payment_content(content):
        Transaction.create({
            'sepay_id': sepay_id,
            'gateway': gateway,
            'transaction_date': transaction_date,
            'account_number': account_number,
            'content': content,
            'transfer_amount': transfer_amount,
            'reference_code': reference_code,
            'status': 'failed',
            'player_name': None,
            'sessions_updated': []
        })
        return jsonify({
            'success': False,
            'message': 'Invalid payment content - missing keywords'
        }), 200

    # First try to find player by short_code (P001, P002, etc.)
    player = extract_player_short_code(content)
    player_name = None

    if player:
        player_name = player['name']
    else:
        # Fall back to extracting player name from content
        player_name = extract_player_name(content)

    if not player_name:
        Transaction.create({
            'sepay_id': sepay_id,
            'gateway': gateway,
            'transaction_date': transaction_date,
            'account_number': account_number,
            'content': content,
            'transfer_amount': transfer_amount,
            'reference_code': reference_code,
            'status': 'failed',
            'player_name': None,
            'sessions_updated': []
        })
        return jsonify({
            'success': False,
            'message': 'Could not extract player from content'
        }), 200

    # Find unpaid sessions for this player
    debt_details = Session.get_all_debts_with_details()
    player_debts = None

    # Case-insensitive player name matching
    for name, details in debt_details.items():
        if name.lower() == player_name.lower():
            player_debts = details
            player_name = name  # Use the exact name from database
            break

    if not player_debts or not player_debts.get('sessions'):
        Transaction.create({
            'sepay_id': sepay_id,
            'gateway': gateway,
            'transaction_date': transaction_date,
            'account_number': account_number,
            'content': content,
            'transfer_amount': transfer_amount,
            'reference_code': reference_code,
            'status': 'success',
            'player_name': player_name,
            'sessions_updated': []
        })
        return jsonify({
            'success': True,
            'message': f'No unpaid sessions found for {player_name}',
            'player_name': player_name,
            'amount_received': transfer_amount,
            'sessions_updated': []
        }), 200

    # Process payments - oldest sessions first
    sessions_updated = []
    remaining_amount = transfer_amount

    # Sort sessions by date (oldest first)
    sorted_sessions = sorted(
        player_debts['sessions'],
        key=lambda x: x['date']
    )

    for session_info in sorted_sessions:
        if remaining_amount <= 0:
            break

        session_id = session_info['session_id']
        owed = session_info['owed']
        current_paid = session_info['amount_paid']

        if owed > 0:
            payment_for_session = min(remaining_amount, owed)
            new_paid = current_paid + payment_for_session

            # Update payment in database
            success = Session.update_participant_payment(
                session_id,
                player_name,
                new_paid
            )

            if success:
                sessions_updated.append({
                    'session_id': session_id,
                    'amount_paid': payment_for_session,
                    'fully_paid': payment_for_session >= owed
                })
                remaining_amount -= payment_for_session

    # Create transaction record
    Transaction.create({
        'sepay_id': sepay_id,
        'gateway': gateway,
        'transaction_date': transaction_date,
        'account_number': account_number,
        'content': content,
        'transfer_amount': transfer_amount,
        'reference_code': reference_code,
        'status': 'success',
        'player_name': player_name,
        'sessions_updated': sessions_updated
    })

    return jsonify({
        'success': True,
        'message': f'Payment processed for {player_name}',
        'player_name': player_name,
        'amount_received': transfer_amount,
        'sessions_updated': len(sessions_updated),
        'remaining_amount': remaining_amount
    }), 200
