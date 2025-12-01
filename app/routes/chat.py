from flask import Blueprint, request, jsonify, render_template
from app.services.ai_service import chat

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/')
def chat_page():
    """Trang chat UI"""
    return render_template('user/chat.html')


@chat_bp.route('/ask', methods=['POST'])
def ask():
    """API endpoint để hỏi AI"""
    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    response = chat(user_message)

    return jsonify({
        'question': user_message,
        'answer': response
    })