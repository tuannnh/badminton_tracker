import json
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.config import Config
from app.models.session import Session
from app.models.player import Player

# Initialize OpenAI client with error handling
client = None


def get_openai_client():
    global client
    if client is not None:
        return client

    if not Config.OPENAI_API_KEY:
        print("[AI] OpenAI API key not configured, using fallback mode")
        return None

    try:
        from openai import OpenAI

        base_url = getattr(Config, 'OPENAI_BASE_URL', None)

        if base_url:
            client = OpenAI(
                api_key=Config.OPENAI_API_KEY,
                base_url=base_url
            )
            print("[AI Service] ✅ OpenAI client initialized.")
            print(f"[AI Service] Using model: {Config.OPENAI_MODEL}")
            print(f"[AI Service] Base URL: {base_url}")
            print(f"[AI Service] client: {client}")
        else:
            client = OpenAI(api_key=Config.OPENAI_API_KEY)

        print(f"[AI] OpenAI client initialized successfully")
        return client
    except Exception as e:
        print(f"[AI] Failed to initialize OpenAI client: {e}")
        return None


def safe_int(value, default=0):
    """Safely convert value to int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_money(amount):
    """Format số tiền an toàn"""
    if amount is None:
        return "0đ"
    try:
        return f"{int(amount):,}đ".replace(",", ".")
    except (ValueError, TypeError):
        return "0đ"


SYSTEM_PROMPT = """Bạn là trợ lý AI cho ứng dụng quản lý cầu lông. 
Nhiệm vụ của bạn là phân tích câu hỏi của người dùng và trả về một JSON object chứa thông tin để query database. 

Các loại query hỗ trợ:
1. player_debt: Tính nợ của một hoặc nhiều người chơi
2. player_sessions: Lấy các buổi chơi của một người
3. all_debts: Lấy danh sách tất cả Người còn chưa thanh toán
4. session_detail: Chi tiết một buổi chơi cụ thể theo ngày
5. monthly_stats: Thống kê theo tháng

Trả về JSON format:
{{
    "query_type": "player_debt|player_sessions|all_debts|session_detail|monthly_stats",
    "player_names": ["tên người chơi 1", "tên người chơi 2"],
    "year": 2025,
    "month": 11,
    "day": null hoặc số ngày (cho session_detail)
}}

Ngày hiện tại: {current_date}

Quy tắc:
- "tháng 11" hoặc "tháng 11/2025" → year: 2025, month: 11
- "ngày 20/11" → year: 2025, month: 11, day: 20
- Nếu không nói năm, mặc định là năm hiện tại
- Nếu user hỏi về nhiều người (VD: "Ly và Mạnh", "Tuấn, Ly"), trả về mảng player_names
- Nếu user hỏi "ai còn nợ" mà không nói tháng cụ thể, để year và month là null để lấy all time
"""

RESPONSE_PROMPT = """Bạn là trợ lý AI cho ứng dụng quản lý cầu lông. 
Dựa trên kết quả query từ database, hãy trả lời câu hỏi của người dùng bằng tiếng Việt.

Quy tắc:
- Trả lời ngắn gọn, rõ ràng và thân thiện
- Format số tiền: 75. 000đ (dùng dấu chấm ngăn cách hàng nghìn)
- Format ngày: DD/MM/YYYY
- Nếu hỏi về nhiều người, liệt kê từng người và tính tổng
- Nếu không có dữ liệu, nói rõ ràng
"""


def find_player_names_in_message(message: str) -> list:
    """Tìm tên người chơi trong message"""
    message_lower = message.lower()
    found_players = []

    try:
        players = Player.find_all()
        for player in players:
            player_name = player.get('name', '')
            if player_name.lower() in message_lower:
                found_players.append(player_name)
    except Exception as e:
        print(f"[AI] Error finding players: {e}")

    return found_players


def parse_user_query(user_message: str) -> dict:
    """Phân tích câu hỏi của người dùng bằng AI hoặc fallback"""
    openai_client = get_openai_client()

    if openai_client:
        current_date = datetime.now().strftime("%Y-%m-%d")
        try:
            response = openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL or 'gpt-4o-mini',
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT.format(current_date=current_date)},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0,
                timeout=15.0
            )
            result = json.loads(response.choices[0].message.content)
            print(f"[AI] Parsed with OpenAI: {result}")

            # Normalize player_names
            player_names = result.get('player_names') or []
            if result.get('player_name'):  # backward compatibility
                player_names = [result['player_name']]

            return {
                'query_type': result.get('query_type', 'all_debts'),
                'player_names': player_names,
                'year': result.get('year'),
                'month': result.get('month'),
                'day': result.get('day')
            }
        except Exception as e:
            print(f"[AI] OpenAI parse error: {e}, using fallback")

    return parse_query_fallback(user_message)


def parse_query_fallback(user_message: str) -> dict:
    """Fallback parser khi không có OpenAI"""
    message = user_message.lower()
    now = datetime.now()

    result = {
        'query_type': 'all_debts',
        'player_names': [],
        'year': None,
        'month': None,
        'day': None
    }

    # Detect all player names in message
    result['player_names'] = find_player_names_in_message(message)

    # Detect month
    month_match = re.search(r'tháng\s*(\d{1,2})', message)
    if month_match:
        result['month'] = int(month_match.group(1))
        result['year'] = now.year

    # Detect year
    year_match = re.search(r'năm\s*(\d{4})|/(\d{4})', message)
    if year_match:
        result['year'] = int(year_match.group(1) or year_match.group(2))

    # Detect day
    day_match = re.search(r'ngày\s*(\d{1,2})', message)
    if day_match:
        result['day'] = int(day_match.group(1))
        result['query_type'] = 'session_detail'
        if result['month'] is None:
            result['month'] = now.month
        if result['year'] is None:
            result['year'] = now.year

    # Detect query type
    if result['player_names']:
        if any(word in message for word in ['nợ', 'thiếu', 'còn', 'owes', 'owe', 'tổng']):
            result['query_type'] = 'player_debt'
        elif any(word in message for word in ['buổi', 'chơi', 'tham gia', 'session']):
            result['query_type'] = 'player_sessions'
    elif 'ai' in message and any(word in message for word in ['nợ', 'thiếu']):
        result['query_type'] = 'all_debts'
    elif any(word in message for word in ['tổng', 'chi phí', 'thống kê', 'summary']):
        result['query_type'] = 'monthly_stats'
        if result['month'] is None:
            result['month'] = now.month
            result['year'] = now.year

    print(f"[AI] Parsed with fallback: {result}")
    return result


def execute_query(query_params: dict) -> dict:
    """Thực thi query dựa trên params"""
    query_type = query_params.get('query_type', 'all_debts')
    player_names = query_params.get('player_names', [])
    year = query_params.get('year')
    month = query_params.get('month')
    day = query_params.get('day')

    # Determine date range
    if year is not None and month is not None:
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1)
        period = f"tháng {month}/{year}"
    else:
        start_date = None
        end_date = None
        period = "tất cả thời gian"

    result = {
        'query_type': query_type,
        'player_names': player_names,
        'period': period,
        'data': None
    }

    try:
        if query_type == 'player_debt':
            if player_names:
                # Query debt for multiple players
                players_data = []
                total_owed_all = 0

                for player_name in player_names:
                    debt_info = Session.get_player_debt(player_name, start_date, end_date)
                    if debt_info:
                        players_data.append({
                            'player_name': player_name,
                            'total_due': safe_int(debt_info.get('total_due', 0)),
                            'total_paid': safe_int(debt_info.get('total_paid', 0)),
                            'total_owed': safe_int(debt_info.get('total_owed', 0)),
                            'sessions_count': safe_int(debt_info.get('sessions_count', 0))
                        })
                        total_owed_all += safe_int(debt_info.get('total_owed', 0))
                    else:
                        players_data.append({
                            'player_name': player_name,
                            'total_due': 0,
                            'total_paid': 0,
                            'total_owed': 0,
                            'sessions_count': 0,
                            'no_data': True
                        })

                result['data'] = {
                    'players': players_data,
                    'total_owed_all': total_owed_all,
                    'player_count': len(player_names)
                }

        elif query_type == 'player_sessions':
            if player_names:
                player_name = player_names[0]  # Only first player for sessions
                sessions = Session.find_by_player(player_name, start_date, end_date)
                result['data'] = {
                    'player_name': player_name,
                    'sessions': []
                }
                for s in sessions:
                    participant = next(
                        (p for p in s.get('participants', [])
                         if p.get('player_name', '').lower() == player_name.lower()),
                        None
                    )
                    result['data']['sessions'].append({
                        'date': s['date'].strftime('%d/%m/%Y') if s.get('date') else 'N/A',
                        'court_name': s.get('court', {}).get('name', ''),
                        'total_cost': s.get('total_cost', 0),
                        'participant': participant
                    })

        elif query_type == 'all_debts':
            if start_date and end_date:
                result['data'] = Session.get_all_debts(start_date, end_date)
            else:
                result['data'] = Session.get_all_debts_all_time()

        elif query_type == 'session_detail':
            if day and month and year:
                session_date = datetime(year, month, day)
                next_day = session_date + relativedelta(days=1)
                sessions = Session.find_by_date_range(session_date, next_day)
                if sessions:
                    session = sessions[0]
                    if player_names:
                        player_name = player_names[0]
                        participant = next(
                            (p for p in session.get('participants', [])
                             if p.get('player_name', '').lower() == player_name.lower()),
                            None
                        )
                        result['data'] = {
                            'date': session['date'].strftime('%d/%m/%Y') if session.get('date') else 'N/A',
                            'total_cost': session.get('total_cost', 0),
                            'participant': participant,
                            'player_name': player_name
                        }
                    else:
                        result['data'] = {
                            'date': session['date'].strftime('%d/%m/%Y') if session.get('date') else 'N/A',
                            'total_cost': session.get('total_cost', 0),
                            'participants_count': len(session.get('participants', [])),
                            'court': session.get('court', {}),
                            'shuttlecock': session.get('shuttlecock', {})
                        }

        elif query_type == 'monthly_stats':
            if year and month:
                summary = Session.get_monthly_summary(year, month)
                result['data'] = {
                    'sessions_count': summary.get('sessions_count', 0),
                    'total_cost': summary.get('total_cost', 0),
                    'total_court': summary.get('total_court', 0),
                    'total_shuttlecock': summary.get('total_shuttlecock', 0),
                    'total_owed': summary.get('total_owed', 0),
                    'debts': summary.get('debts', [])
                }
            else:
                all_sessions = Session.find_all(limit=500)
                total_cost = sum(s.get('total_cost', 0) for s in all_sessions)
                total_owed_info = Session.get_total_owed_all_time()
                result['data'] = {
                    'sessions_count': len(all_sessions),
                    'total_cost': total_cost,
                    'total_owed': total_owed_info.get('total_owed', 0),
                    'debts': Session.get_all_debts_all_time()
                }

    except Exception as e:
        print(f"[AI] Query execution error: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)

    return result


def generate_response(user_message: str, query_result: dict) -> str:
    """Tạo câu trả lời từ kết quả query"""
    openai_client = get_openai_client()

    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL or 'gpt-4o-mini',
                messages=[
                    {"role": "system", "content": RESPONSE_PROMPT},
                    {"role": "user", "content": f"""Câu hỏi: {user_message}

Kết quả từ database:
{json.dumps(query_result, default=str, ensure_ascii=False, indent=2)}"""}
                ],
                temperature=0.7,
            timeout = 15.0
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[AI] OpenAI response error: {e}, using fallback")

    return generate_response_fallback(query_result)


def generate_response_fallback(query_result: dict) -> str:
    """Fallback response khi không có OpenAI"""
    query_type = query_result.get('query_type')
    data = query_result.get('data')
    player_names = query_result.get('player_names', [])
    period = query_result.get('period', '')
    error = query_result.get('error')

    if error:
        return f"Xin lỗi, có lỗi xảy ra: {error}"

    if not data:
        if query_type == 'all_debts':
            return f"🎉 Không còn ai chưa thanh toán trong {period}!"
        return f"Không tìm thấy dữ liệu cho {period}."

    if query_type == 'player_debt':
        players = data.get('players', [])
        total_owed_all = safe_int(data.get('total_owed_all', 0))

        if len(players) == 1:
            # Single player
            p = players[0]
            if p.get('no_data'):
                return f"Không tìm thấy dữ liệu cho **{p['player_name']}** trong {period}."

            total_owed = safe_int(p.get('total_owed', 0))
            if total_owed > 0:
                return f"""💰 **{p['player_name']}** còn nợ **{format_money(total_owed)}** trong {period}. 

📊 Chi tiết:
- Tổng phải trả: {format_money(p.get('total_due', 0))}
- Đã trả: {format_money(p.get('total_paid', 0))}
- Số buổi: {p.get('sessions_count', 0)}"""
            else:
                return f"✅ **{p['player_name']}** đã thanh toán đủ trong {period}!"

        else:
            # Multiple players
            lines = [f"💰 **Tổng nợ của {len(players)} người** trong {period}:\n"]

            for p in players:
                if p.get('no_data'):
                    lines.append(f"- **{p['player_name']}**: _Không có dữ liệu_")
                else:
                    owed = safe_int(p.get('total_owed', 0))
                    if owed > 0:
                        lines.append(
                            f"- **{p['player_name']}**: {format_money(owed)} ({p.get('sessions_count', 0)} buổi)")
                    else:
                        lines.append(f"- **{p['player_name']}**: ✅ Đã thanh toán đủ")

            lines.append(f"\n🧮 **Tổng cộng: {format_money(total_owed_all)}**")
            return "\n".join(lines)

    elif query_type == 'player_sessions':
        player_name = data.get('player_name', '')
        sessions = data.get('sessions', [])

        if not sessions:
            return f"**{player_name}** chưa tham gia buổi chơi nào trong {period}."

        lines = [f"🏸 **{player_name}** đã chơi **{len(sessions)} buổi** trong {period}:\n"]
        total = 0
        total_owed = 0

        for s in sessions:
            p = s.get('participant') or {}
            amount = safe_int(p.get('amount_due', 0))
            paid = safe_int(p.get('amount_paid', 0))
            owed = amount - paid
            is_paid = p.get('is_paid', False)
            status = "✅" if is_paid else f"❌ còn nợ {format_money(owed)}"
            lines.append(f"- {s.get('date', 'N/A')}: {format_money(amount)} {status}")
            total += amount
            if not is_paid:
                total_owed += owed

        lines.append(f"\n💵 **Tổng: {format_money(total)}**")
        if total_owed > 0:
            lines.append(f"⚠️ **Còn nợ: {format_money(total_owed)}**")
        return "\n".join(lines)

    elif query_type == 'all_debts':
        if not data or len(data) == 0:
            return f"🎉 Tuyệt vời! Không còn ai chưa thanh toán trong {period}!"

        total_all = sum(safe_int(d.get('total_owed', 0)) for d in data)
        lines = [f"📋 **Danh sách người còn chưa thanh toán** ({period}):\n"]
        lines.append(f"💰 Tổng nợ: **{format_money(total_all)}**\n")

        for d in data:
            name = d.get('_id', 'Unknown')
            owed = safe_int(d.get('total_owed', 0))
            sessions = safe_int(d.get('sessions_count', 0))
            lines.append(f"- **{name}**: {format_money(owed)} ({sessions} buổi)")
        return "\n".join(lines)

    elif query_type == 'session_detail':
        date_str = data.get('date', 'N/A')
        player_name = data.get('player_name')

        if player_name and data.get('participant'):
            p = data['participant']
            amount_due = safe_int(p.get('amount_due', 0))
            amount_paid = safe_int(p.get('amount_paid', 0))
            owed = amount_due - amount_paid
            status = "✅ Đã trả đủ" if p.get('is_paid') else f"❌ Còn nợ {format_money(owed)}"
            return f"""📅 **Buổi chơi ngày {date_str}**

👤 **{player_name}**:
- Phải trả: {format_money(amount_due)}
- Đã trả: {format_money(amount_paid)}
- Trạng thái: {status}"""
        else:
            return f"""📅 **Buổi chơi ngày {date_str}**

- 👥 Số người: {safe_int(data.get('participants_count', 0))}
- 💵 Tổng chi phí: {format_money(data.get('total_cost', 0))}"""

    elif query_type == 'monthly_stats':
        sessions_count = safe_int(data.get('sessions_count', 0))
        total_cost = safe_int(data.get('total_cost', 0))
        total_court = safe_int(data.get('total_court', 0))
        total_shuttlecock = safe_int(data.get('total_shuttlecock', 0))
        total_owed = safe_int(data.get('total_owed', 0))

        return f"""📊 **Thống kê {period}:**

🏸 Số buổi chơi: **{sessions_count}**
💵 Tổng chi phí: **{format_money(total_cost)}**
   - Tiền sân: {format_money(total_court)}
   - Tiền cầu: {format_money(total_shuttlecock)}
⚠️ Tổng chưa thanh toán: **{format_money(total_owed)}**"""

    return "Xin lỗi, tôi không hiểu câu hỏi.  Vui lòng thử lại với các câu như:\n- \"Ai còn nợ?\"\n- \"Ly còn nợ bao nhiêu?\"\n- \"Tổng tiền Ly và Mạnh còn thiếu?\"\n- \"Thống kê tháng 11\""


def chat(user_message: str) -> str:
    """Main function để xử lý chat"""
    try:
        # Step 1: Parse user query
        query_params = parse_user_query(user_message)

        # Step 2: Execute query
        query_result = execute_query(query_params)

        # Step 3: Generate response
        response = generate_response(user_message, query_result)

        return response

    except Exception as e:
        print(f"[AI] Chat error: {e}")
        import traceback
        traceback.print_exc()
        return "Xin lỗi, có lỗi xảy ra.  Vui lòng thử lại."