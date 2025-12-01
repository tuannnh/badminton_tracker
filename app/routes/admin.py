from flask import Blueprint, render_template, request, redirect, url_for, flash, session as flask_session
from datetime import datetime
from dateutil.relativedelta import relativedelta
from bson import ObjectId
from functools import wraps

from app.models.session import Session
from app.models.player import Player
from app.models.user import User
from app.models.settings import Settings

admin_bp = Blueprint('admin', __name__)


# ==========================================
# Authentication
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not flask_session.get('admin_logged_in'):
            flash('Vui lòng đăng nhập để tiếp tục', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if flask_session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.authenticate(username, password)

        if user:
            flask_session['admin_logged_in'] = True
            flask_session['admin_username'] = user['username']
            flask_session['admin_user_id'] = str(user['_id'])
            flash('Đăng nhập thành công! ', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Sai tên đăng nhập hoặc mật khẩu', 'error')

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    flask_session.clear()
    flash('Đã đăng xuất', 'success')
    return redirect(url_for('admin.login'))


@admin_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Đổi mật khẩu"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user = User.find_by_id(flask_session.get('admin_user_id'))

        if not user:
            flash('Không tìm thấy user', 'error')
            return redirect(url_for('admin.dashboard'))

        if not User.check_password(current_password, user['password_hash']):
            flash('Mật khẩu hiện tại không đúng', 'error')
            return render_template('admin/change_password.html')

        if new_password != confirm_password:
            flash('Mật khẩu mới không khớp', 'error')
            return render_template('admin/change_password.html')

        if len(new_password) < 6:
            flash('Mật khẩu mới phải có ít nhất 6 ký tự', 'error')
            return render_template('admin/change_password.html')

        User.update_password(user['_id'], new_password)
        flash('Đã đổi mật khẩu thành công!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/change_password.html')


@admin_bp.route('/')
@login_required
def dashboard():
    """Admin Dashboard"""
    now = datetime.now()
    summary = Session.get_monthly_summary(now.year, now.month)
    recent_sessions = Session.find_all(limit=10)
    players = Player.find_all()

    # Debts
    all_time_debts = Session.get_all_debts_all_time()
    total_owed_all_time = Session.get_total_owed_all_time()

    # To receive
    all_time_to_receive = Session.get_all_to_receive_all_time()
    total_to_receive_all_time = Session.get_total_to_receive_all_time()

    return render_template('admin/dashboard.html',
                           summary=summary,
                           recent_sessions=recent_sessions,
                           players=players,
                           current_month=now.strftime("%m/%Y"),
                           all_time_debts=all_time_debts,
                           total_owed_all_time=total_owed_all_time,
                           all_time_to_receive=all_time_to_receive,
                           total_to_receive_all_time=total_to_receive_all_time)


# ==========================================
# Sessions Management
# ==========================================

@admin_bp.route('/sessions')
@login_required
def sessions():
    """Danh sách buổi chơi"""
    now = datetime.now()
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    # Smart default
    if year is None or month is None:
        current_start = datetime(now.year, now.month, 1)
        current_end = current_start + relativedelta(months=1)
        current_sessions = Session.find_by_date_range(current_start, current_end)

        if current_sessions:
            year = now.year
            month = now.month
        else:
            prev = now - relativedelta(months=1)
            year = prev.year
            month = prev.month

    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    sessions_list = Session.find_by_date_range(start_date, end_date)
    summary = Session.get_monthly_summary(year, month)
    available_months = Session.get_available_months()

    return render_template('admin/sessions.html',
                           sessions=sessions_list,
                           summary=summary,
                           selected_year=year,
                           selected_month=month,
                           available_months=available_months)


@admin_bp.route('/sessions/new', methods=['GET', 'POST'])
@login_required
def session_new():
    """Tạo buổi chơi mới"""
    players = Player.find_all()
    court_payer = Player.get_default_court_payer()
    shuttlecock_payer = Player.get_default_shuttlecock_payer()
    defaults = Settings.get_defaults()

    if request.method == 'POST':
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')

        # Court info
        price_per_hour = int(request.form['price_per_hour'])
        total_hours = float(request.form['total_hours'])
        court_payer_id = request.form.get('court_payer_id', str(court_payer['_id']) if court_payer else '')
        court_payer_doc = Player.find_by_id(court_payer_id) if court_payer_id else None
        total_court_price = int(price_per_hour * total_hours)

        court = {
            'name': request.form.get('court_name', ''),
            'location': request.form.get('court_location', ''),
            'price_per_hour': price_per_hour,
            'total_hours': total_hours,
            'total_court_price': total_court_price,
            'paid_by': {
                'player_id': ObjectId(court_payer_id) if court_payer_id else None,
                'player_name': court_payer_doc['name'] if court_payer_doc else ''
            }
        }

        # Shuttlecock info
        shuttlecock_qty = int(request.form['shuttlecock_quantity'])
        shuttlecock_price = int(request.form['price_per_shuttlecock'])
        shuttlecock_payer_id = request.form.get('shuttlecock_payer_id',
                                                str(shuttlecock_payer['_id']) if shuttlecock_payer else '')
        shuttlecock_payer_doc = Player.find_by_id(shuttlecock_payer_id) if shuttlecock_payer_id else None
        total_shuttlecock_price = shuttlecock_qty * shuttlecock_price

        shuttlecock = {
            'quantity': shuttlecock_qty,
            'price_per_shuttlecock': shuttlecock_price,
            'total_shuttlecock_price': total_shuttlecock_price,
            'paid_by': {
                'player_id': ObjectId(shuttlecock_payer_id) if shuttlecock_payer_id else None,
                'player_name': shuttlecock_payer_doc['name'] if shuttlecock_payer_doc else ''
            }
        }

        # Calculate totals
        total_cost = total_court_price + total_shuttlecock_price
        participant_ids = request.form.getlist('participants')

        if not participant_ids:
            flash('Vui lòng chọn ít nhất 1 người chơi', 'error')
            return render_template('admin/session_form.html',
                                   players=players,
                                   court_payer=court_payer,
                                   shuttlecock_payer=shuttlecock_payer,
                                   defaults=defaults,
                                   session_data=None,
                                   is_edit=False)

        # Calculate amount per person
        num_participants = len(participant_ids)
        amount_per_person = round(total_cost / num_participants)

        # Build participants list with pre-paid amounts
        participants = []
        for pid in participant_ids:
            player = Player.find_by_id(pid)
            player_name = player['name']

            # Calculate pre-paid amount (người trả sân/cầu đã trả trước)
            pre_paid = 0

            # Nếu người này là người trả tiền sân
            if court_payer_id and str(player['_id']) == court_payer_id:
                pre_paid += total_court_price

            # Nếu người này là người trả tiền cầu
            if shuttlecock_payer_id and str(player['_id']) == shuttlecock_payer_id:
                pre_paid += total_shuttlecock_price

            # Tính số tiền thực tế cần trả/nhận
            # amount_due = số tiền phải chia đều
            # amount_paid = số tiền đã trả (bao gồm pre-paid)
            # Nếu pre_paid > amount_due → người này được nhận lại tiền

            participants.append({
                'player_id': ObjectId(pid),
                'player_name': player_name,
                'amount_due': amount_per_person,
                'amount_paid': min(pre_paid, amount_per_person),  # Đã trả tối đa = số phải trả
                'amount_pre_paid': pre_paid,  # Tổng số đã trả trước
                'amount_to_receive': max(0, pre_paid - amount_per_person),  # Số tiền được nhận lại
                'is_paid': pre_paid >= amount_per_person,
                'paid_at': datetime.now() if pre_paid >= amount_per_person else None,
                'note': 'Trả tiền sân' if (court_payer_id and str(player['_id']) == court_payer_id) else (
                    'Trả tiền cầu' if (shuttlecock_payer_id and str(player['_id']) == shuttlecock_payer_id) else ''
                )
            })

        Session.create({
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'court': court,
            'shuttlecock': shuttlecock,
            'participants': participants,
            'status': 'completed',
            'note': request.form.get('note', '')
        })

        flash('Đã tạo buổi chơi mới thành công!', 'success')
        return redirect(url_for('admin.sessions'))

    return render_template('admin/session_form.html',
                           players=players,
                           court_payer=court_payer,
                           shuttlecock_payer=shuttlecock_payer,
                           defaults=defaults,
                           session_data=None,
                           is_edit=False)


@admin_bp.route('/sessions/<session_id>/edit', methods=['GET', 'POST'])
@login_required
def session_edit(session_id):
    """Sửa buổi chơi"""
    session_doc = Session.find_by_id(session_id)
    if not session_doc:
        flash('Không tìm thấy buổi chơi', 'error')
        return redirect(url_for('admin. sessions'))

    players = Player.find_all()
    court_payer = Player.get_default_court_payer()
    shuttlecock_payer = Player.get_default_shuttlecock_payer()
    defaults = Settings.get_defaults()

    if request.method == 'POST':
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')

        # Court info
        price_per_hour = int(request.form['price_per_hour'])
        total_hours = float(request.form['total_hours'])
        court_payer_id = request.form.get('court_payer_id')
        court_payer_doc = Player.find_by_id(court_payer_id)
        total_court_price = int(price_per_hour * total_hours)

        court = {
            'name': request.form.get('court_name', ''),
            'location': request.form.get('court_location', ''),
            'price_per_hour': price_per_hour,
            'total_hours': total_hours,
            'total_court_price': total_court_price,
            'paid_by': {
                'player_id': ObjectId(court_payer_id),
                'player_name': court_payer_doc['name']
            }
        }

        # Shuttlecock info
        shuttlecock_qty = int(request.form['shuttlecock_quantity'])
        shuttlecock_price = int(request.form['price_per_shuttlecock'])
        shuttlecock_payer_id = request.form.get('shuttlecock_payer_id')
        shuttlecock_payer_doc = Player.find_by_id(shuttlecock_payer_id)
        total_shuttlecock_price = shuttlecock_qty * shuttlecock_price

        shuttlecock = {
            'quantity': shuttlecock_qty,
            'price_per_shuttlecock': shuttlecock_price,
            'total_shuttlecock_price': total_shuttlecock_price,
            'paid_by': {
                'player_id': ObjectId(shuttlecock_payer_id),
                'player_name': shuttlecock_payer_doc['name']
            }
        }

        # Calculate totals
        total_cost = total_court_price + total_shuttlecock_price
        participant_ids = request.form.getlist('participants')
        num_participants = len(participant_ids)
        amount_per_person = round(total_cost / num_participants)

        # Get existing payment info
        existing_payments = {str(p['player_id']): p for p in session_doc['participants']}

        # Build participants list
        participants = []
        for pid in participant_ids:
            player = Player.find_by_id(pid)
            player_name = player['name']
            existing = existing_payments.get(pid, {})

            # Calculate pre-paid amount
            pre_paid = 0
            if str(player['_id']) == court_payer_id:
                pre_paid += total_court_price
            if str(player['_id']) == shuttlecock_payer_id:
                pre_paid += total_shuttlecock_price

            # Keep manually updated payment if exists, otherwise use pre-paid
            manual_paid = existing.get('amount_paid', 0)
            # Nếu đã có payment thủ công và không phải người trả sân/cầu
            if pid in existing_payments and pre_paid == 0:
                amount_paid = manual_paid
            else:
                amount_paid = min(pre_paid, amount_per_person)

            participants.append({
                'player_id': ObjectId(pid),
                'player_name': player_name,
                'amount_due': amount_per_person,
                'amount_paid': amount_paid,
                'amount_pre_paid': pre_paid,
                'amount_to_receive': max(0, pre_paid - amount_per_person),
                'is_paid': (pre_paid >= amount_per_person) or (manual_paid >= amount_per_person),
                'paid_at': existing.get('paid_at') if (
                        pre_paid >= amount_per_person or manual_paid >= amount_per_person) else None,
                'note': existing.get('note', '')
            })

        Session.update(session_id, {
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'court': court,
            'shuttlecock': shuttlecock,
            'total_cost': total_cost,
            'participants': participants,
            'note': request.form.get('note', '')
        })

        flash('Đã cập nhật buổi chơi thành công!', 'success')
        return redirect(url_for('admin.session_detail', session_id=session_id))

    return render_template('admin/session_form.html',
                           players=players,
                           court_payer=court_payer,
                           shuttlecock_payer=shuttlecock_payer,
                           defaults=defaults,
                           session_data=session_doc,
                           is_edit=True)


@admin_bp.route('/sessions/<session_id>')
@login_required
def session_detail(session_id):
    """Chi tiết buổi chơi"""
    session_doc = Session.find_by_id(session_id)
    if not session_doc:
        flash('Không tìm thấy buổi chơi', 'error')
        return redirect(url_for('admin.sessions'))

    return render_template('admin/session_detail.html', session_data=session_doc)


@admin_bp.route('/sessions/<session_id>/delete', methods=['POST'])
@login_required
def session_delete(session_id):
    """Xóa buổi chơi"""
    Session.delete(session_id)
    flash('Đã xóa buổi chơi', 'success')
    return redirect(url_for('admin.sessions'))


@admin_bp.route('/sessions/<session_id>/payment', methods=['POST'])
@login_required
def update_payment(session_id):
    """Cập nhật thanh toán"""
    player_name = request.form['player_name']
    amount_paid = int(request.form['amount_paid'])

    Session.update_participant_payment(session_id, player_name, amount_paid)

    flash(f'Đã cập nhật thanh toán cho {player_name}', 'success')
    return redirect(url_for('admin.session_detail', session_id=session_id))


@admin_bp.route('/sessions/<session_id>/mark-paid/<player_name>', methods=['POST'])
@login_required
def mark_paid(session_id, player_name):
    """Đánh dấu đã trả đủ"""
    session_doc = Session.find_by_id(session_id)
    if session_doc:
        for p in session_doc['participants']:
            if p['player_name'] == player_name:
                Session.update_participant_payment(session_id, player_name, p['amount_due'])
                flash(f'{player_name} đã trả đủ! ', 'success')
                break

    referrer = request.referrer
    if referrer and 'quick-payment' in referrer:
        return redirect(referrer)
    return redirect(url_for('admin.session_detail', session_id=session_id))


# ==========================================
# Quick Payment
# ==========================================
@admin_bp.route('/quick-payment')
@login_required
def quick_payment():
    """Trang thanh toán nhanh"""
    view_type = request.args.get('type', 'owed')  # 'owed' or 'receive'

    debt_details = Session.get_all_debts_with_details()
    receive_details = Session.get_all_to_receive_with_details()
    players = Player.find_all()

    return render_template('admin/quick_payment.html',
                           debt_details=debt_details,
                           receive_details=receive_details,
                           players=players,
                           view_type=view_type)


@admin_bp.route('/quick-payment/mark-all-paid', methods=['POST'])
@login_required
def mark_all_paid():
    """Đánh dấu một người đã trả hết tất cả tiền chưa thanh toán"""
    player_name = request.form['player_name']

    all_sessions = Session.find_all(limit=500)

    count = 0
    for session_doc in all_sessions:
        for p in session_doc['participants']:
            # Chỉ cập nhật những Người còn chưa thanh toán (không phải người được nhận lại)
            if p['player_name'] == player_name and not p.get('is_paid', False) and p.get('amount_to_receive', 0) == 0:
                Session.update_participant_payment(
                    str(session_doc['_id']),
                    player_name,
                    p['amount_due']
                )
                count += 1

    flash(f'Đã cập nhật {count} buổi cho {player_name}', 'success')
    return redirect(url_for('admin.quick_payment'))


@admin_bp.route('/quick-payment/mark-received', methods=['POST'])
@login_required
def mark_received():
    """Đánh dấu đã trả lại tiền cho một người"""
    player_name = request.form['player_name']

    all_sessions = Session.find_all(limit=500)

    count = 0
    total_returned = 0
    for session_doc in all_sessions:
        for p in session_doc['participants']:
            if p['player_name'] == player_name and p.get('amount_to_receive', 0) > 0:
                # Đánh dấu đã trả lại bằng cách set amount_to_receive = 0 và thêm note
                Session.update_participant_received(
                    str(session_doc['_id']),
                    player_name
                )
                total_returned += p.get('amount_to_receive', 0)
                count += 1

    flash(f'Đã trả lại {count} buổi ({total_returned:,}đ) cho {player_name}'.replace(',', '. '), 'success')
    return redirect(url_for('admin. quick_payment', type='receive'))


# ==========================================
# Players Management
# ==========================================

@admin_bp.route('/players')
@login_required
def players():
    """Danh sách người chơi"""
    players_list = Player.find_all(active_only=False)
    return render_template('admin/players.html', players=players_list)


@admin_bp.route('/players/new', methods=['POST'])
@login_required
def player_new():
    """Thêm người chơi mới"""
    Player.create({
        'name': request.form['name'],
        'phone': request.form.get('phone'),
        'email': request.form.get('email'),
        'is_default_court_payer': request.form.get('is_default_court_payer') == 'on',
        'is_default_shuttlecock_payer': request.form.get('is_default_shuttlecock_payer') == 'on',
        'is_admin': request.form.get('is_admin') == 'on'
    })
    flash('Đã thêm người chơi mới', 'success')
    return redirect(url_for('admin.players'))


@admin_bp.route('/players/<player_id>/edit', methods=['POST'])
@login_required
def player_edit(player_id):
    """Sửa người chơi"""
    Player.update(player_id, {
        'name': request.form['name'],
        'phone': request.form.get('phone'),
        'email': request.form.get('email'),
        'is_default_court_payer': request.form.get('is_default_court_payer') == 'on',
        'is_default_shuttlecock_payer': request.form.get('is_default_shuttlecock_payer') == 'on',
        'is_admin': request.form.get('is_admin') == 'on'
    })
    flash('Đã cập nhật thông tin người chơi', 'success')
    return redirect(url_for('admin.players'))


@admin_bp.route('/players/<player_id>/delete', methods=['POST'])
@login_required
def player_delete(player_id):
    """Xóa người chơi (soft delete)"""
    Player.delete(player_id)
    flash('Đã xóa người chơi', 'success')
    return redirect(url_for('admin.players'))


@admin_bp.route('/players/<player_id>/stats')
@login_required
def player_stats(player_id):
    """Thống kê người chơi"""
    player = Player.find_by_id(player_id)
    if not player:
        flash('Không tìm thấy người chơi', 'error')
        return redirect(url_for('admin.players'))

    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    sessions_list = Session.find_by_player(player['name'], start_date, end_date)
    debt_info = Session.get_player_debt(player['name'], start_date, end_date)

    return render_template('admin/player_stats.html',
                           player=player,
                           sessions=sessions_list,
                           debt_info=debt_info,
                           selected_year=year,
                           selected_month=month)


# ==========================================
# Settings Management
# ==========================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Quản lý cài đặt"""
    if request.method == 'POST':
        # Update settings
        Settings.set('default_court_name', request.form.get('default_court_name', ''))
        Settings.set('default_court_location', request.form.get('default_court_location', ''))
        Settings.set('default_court_price_per_hour', int(request.form.get('default_court_price_per_hour', 139000)))
        Settings.set('default_total_hours', float(request.form.get('default_total_hours', 2)))
        Settings.set('default_start_time', request.form.get('default_start_time', '14:40'))
        Settings.set('default_end_time', request.form.get('default_end_time', '16:45'))
        Settings.set('default_shuttlecock_price', int(request.form.get('default_shuttlecock_price', 25000)))
        Settings.set('default_shuttlecock_quantity', int(request.form.get('default_shuttlecock_quantity', 5)))

        flash('Đã lưu cài đặt! ', 'success')
        return redirect(url_for('admin.settings'))

    defaults = Settings.get_defaults()
    return render_template('admin/settings.html', defaults=defaults)
