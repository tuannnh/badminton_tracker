from flask import Blueprint, render_template, request
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.models.session import Session
from app.models.player import Player

user_bp = Blueprint('user', __name__)


@user_bp. route('/')
def index():
    """Trang chủ - Dashboard người dùng"""
    now = datetime.now()

    # Current month summary
    current_summary = Session.get_monthly_summary(now.year, now.month)

    # Previous month summary
    prev_month = now - relativedelta(months=1)
    prev_summary = Session. get_monthly_summary(prev_month. year, prev_month.month)

    # Recent sessions
    recent_sessions = Session.find_all(limit=5)

    # All time debts
    all_time_debts = Session.get_all_debts_all_time()
    total_owed_all_time = Session.get_total_owed_all_time()

    # All time to receive
    all_time_to_receive = Session.get_all_to_receive_all_time()
    total_to_receive_all_time = Session.get_total_to_receive_all_time()

    # Get months with debts
    months_with_debts = Session.get_months_with_debts()

    return render_template('user/index.html',
                           current_summary=current_summary,
                           prev_summary=prev_summary,
                           recent_sessions=recent_sessions,
                           current_month=now. strftime("%m/%Y"),
                           prev_month_str=prev_month. strftime("%m/%Y"),
                           all_time_debts=all_time_debts,
                           total_owed_all_time=total_owed_all_time,
                           all_time_to_receive=all_time_to_receive,
                           total_to_receive_all_time=total_to_receive_all_time,
                           months_with_debts=months_with_debts,
                           now=now)


@user_bp.route('/sessions')
def sessions():
    """Danh sách các buổi chơi"""
    now = datetime.now()

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

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
            month = prev. month

    player = request.args.get('player', '')

    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    if player:
        sessions_list = Session.find_by_player(player, start_date, end_date)
    else:
        sessions_list = Session.find_by_date_range(start_date, end_date)

    summary = Session.get_monthly_summary(year, month)
    players = Player.find_all()
    available_months = Session.get_available_months()

    return render_template('user/sessions.html',
                           sessions=sessions_list,
                           summary=summary,
                           players=players,
                           selected_year=year,
                           selected_month=month,
                           selected_player=player,
                           available_months=available_months)


@user_bp.route('/sessions/<session_id>')
def session_detail(session_id):
    """Chi tiết một buổi chơi"""
    session = Session.find_by_id(session_id)
    if not session:
        return "Session not found", 404

    return render_template('user/session_detail.html', session=session)


@user_bp.route('/debts')
def debts():
    """Trang xem nợ và tiền nhận lại"""
    view_type = request. args.get('type', 'owed')  # 'owed' or 'receive'

    year = request.args. get('year', type=int)
    month = request.args.get('month', type=int)

    if year and month:
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1)
        filter_label = f"Tháng {month}/{year}"
    else:
        start_date = None
        end_date = None
        filter_label = "Tất cả"

    if view_type == 'receive':
        # Hiển thị người được nhận lại tiền
        if start_date and end_date:
            data_list = Session.get_all_to_receive(start_date, end_date)
            details = Session.get_to_receive_with_details_by_month(year, month)
        else:
            data_list = Session. get_all_to_receive_all_time()
            details = Session.get_all_to_receive_with_details()

        total_amount = sum(d['total_to_receive'] for d in data_list)
        page_title = "Người được nhận lại tiền"
        amount_field = 'total_to_receive'
    else:
        # Hiển thị người còn nợ
        if start_date and end_date:
            data_list = Session.get_all_debts(start_date, end_date)
            details = Session.get_debts_with_details_by_month(year, month)
        else:
            data_list = Session.get_all_debts_all_time()
            details = Session. get_all_debts_with_details()

        total_amount = sum(d['total_owed'] for d in data_list)
        page_title = "Người còn chưa thanh toán"
        amount_field = 'total_owed'

    months_with_debts = Session.get_months_with_debts()

    return render_template('user/debts.html',
                           data_list=data_list,
                           details=details,
                           total_amount=total_amount,
                           people_count=len(data_list),
                           filter_label=filter_label,
                           selected_year=year,
                           selected_month=month,
                           months_with_debts=months_with_debts,
                           view_type=view_type,
                           page_title=page_title,
                           amount_field=amount_field)