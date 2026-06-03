import json
import urllib.request
import urllib.error
from collections import Counter
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from ..models import Book, Category, Order, ChatSession, ChatMessage


# ── CHAT – KHÁCH HÀNG GỬI TIN ────────────────────────────────────────────────
@login_required
@require_POST
def customer_send(request):
    if request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    data = json.loads(request.body)
    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)

    session, _ = ChatSession.objects.get_or_create(customer=request.user)
    session.last_message_at = timezone.now()
    session.save(update_fields=['last_message_at'])

    msg = ChatMessage.objects.create(session=session, sender=request.user, content=content)
    return JsonResponse({'id': msg.id, 'created_at': msg.created_at.strftime('%H:%M')})


# ── CHAT – KHÁCH HÀNG POLL TIN MỚI ──────────────────────────────────────────
@login_required
@require_GET
def customer_poll(request):
    if request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    after_id = int(request.GET.get('after', 0))
    is_history = request.GET.get('history') == '1'

    try:
        session = ChatSession.objects.get(customer=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({'messages': []})

    if is_history and after_id == 0:
        msgs = session.messages.select_related('sender').all()
    else:
        msgs = session.messages.filter(id__gt=after_id).select_related('sender')

    session.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'content': m.content,
                'is_mine': m.sender_id == request.user.id,
                'created_at': m.created_at.strftime('%H:%M'),
            }
            for m in msgs
        ]
    })


# ── CHAT – STAFF: DANH SÁCH SESSION ──────────────────────────────────────────
@login_required
@require_GET
def staff_sessions(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    sessions = ChatSession.objects.select_related('customer').prefetch_related('messages')
    result = []
    for s in sessions:
        last = s.last_message()
        result.append({
            'id': s.id,
            'customer_name': s.customer.get_full_name() or s.customer.username,
            'customer_id': s.customer.id,
            'unread': s.unread_for_staff(),
            'last_message': last.content[:60] if last else '',
            'last_time': last.created_at.strftime('%H:%M') if last else '',
        })

    return JsonResponse({'sessions': result, 'total_unread': sum(s['unread'] for s in result)})


# ── CHAT – STAFF POLL TIN MỚI ─────────────────────────────────────────────────
@login_required
@require_GET
def staff_poll(request, session_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'messages': []})

    after_id = int(request.GET.get('after', 0))
    msgs = session.messages.select_related('sender').all() if after_id == 0 \
        else session.messages.filter(id__gt=after_id).select_related('sender')

    session.messages.filter(sender=session.customer, is_read=False).update(is_read=True)

    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'content': m.content,
                'is_mine': m.sender.is_staff,
                'sender_name': m.sender.get_full_name() or m.sender.username,
                'created_at': m.created_at.strftime('%H:%M'),
            }
            for m in msgs
        ]
    })


# ── CHAT – STAFF GỬI TIN ──────────────────────────────────────────────────────
@login_required
@require_POST
def staff_send(request, session_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session không tồn tại'}, status=404)

    data = json.loads(request.body)
    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)

    session.last_message_at = timezone.now()
    session.save(update_fields=['last_message_at'])

    msg = ChatMessage.objects.create(session=session, sender=request.user, content=content)
    return JsonResponse({'id': msg.id, 'created_at': msg.created_at.strftime('%H:%M')})


# ── AI CHATBOT (SERVER-SIDE) ──────────────────────────────────────────────────
@login_required
@require_POST
def chat_bot(request):
    """
    Endpoint AI Bot: nhận tin nhắn + history từ client, thu thập context thực
    từ DB (đơn hàng + tracking, wishlist, lịch sử xem, sở thích theo danh mục,
    sách mới/bán chạy), rồi gọi Anthropic API từ server.
    API key đặt trong settings.py (ANTHROPIC_API_KEY).
    """
    from django.conf import settings as django_settings

    # Rate limit đơn giản: tối đa 1 request mỗi 2 giây per user
    last_call = request.session.get('bot_last_call', 0)
    now_ts = timezone.now().timestamp()
    if now_ts - last_call < 2:
        return JsonResponse({'error': 'Vui lòng chờ một chút trước khi gửi tiếp.'}, status=429)
    request.session['bot_last_call'] = now_ts

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = data.get('message', '').strip()
    history      = data.get('history', [])
    if not user_message:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)

    user         = request.user
    user_display = user.get_full_name() or user.username

    # ── 1. Đơn hàng + tracking chi tiết ──────────────────────────────────────
    recent_orders = (
        Order.objects
        .filter(user=user)
        .prefetch_related('items__book', 'trackings')
        .order_by('-created_at')[:5]
    )
    if recent_orders:
        order_lines = []
        for o in recent_orders:
            items_str = ", ".join(
                f"{i.book.title} (x{i.quantity}, {i.price:,.0f}đ/cuốn)"
                for i in o.items.all()
            )
            # Lấy bước tracking mới nhất
            last_track = o.trackings.order_by('-created_at').first()
            track_msg  = f" | Tracking: {last_track.message}" if last_track else ""
            ship_info  = f" | Đơn vị ship: {o.shipping_unit}" if o.shipping_unit else ""
            order_lines.append(
                f"  • Đơn #{o.id} [{o.get_status_display()}]{ship_info}"
                f" | {o.created_at.strftime('%d/%m/%Y')} | Tổng: {o.total_price:,.0f}đ"
                f" | Sách: {items_str}{track_msg}"
            )
        orders_info = "ĐƠN HÀNG GẦN ĐÂY:\n" + "\n".join(order_lines)
    else:
        orders_info = "ĐƠN HÀNG: Khách chưa có đơn hàng nào."

    # ── 2. Wishlist + suy ra sở thích theo danh mục ───────────────────────────
    wishlist_qs = (
        Book.objects
        .filter(wishlist=user)
        .select_related('category')[:10]
    )
    if wishlist_qs:
        wishlist_lines = [
            f"  • {b.title} – {b.author}"
            f"{' [' + b.category.name + ']' if b.category else ''}"
            f" – {b.price:,.0f}đ"
            f"{' (còn hàng)' if b.stock > 0 else ' (hết hàng)'}"
            for b in wishlist_qs
        ]
        # Tần suất danh mục để suy sở thích
        cat_counter  = Counter(
            b.category.name for b in wishlist_qs if b.category
        )
        fav_cats     = ", ".join(
            f"{cat} ({cnt} cuốn)" for cat, cnt in cat_counter.most_common(3)
        )
        wishlist_info = (
            "WISHLIST:\n" + "\n".join(wishlist_lines)
            + (f"\n  → Sở thích nổi bật: {fav_cats}" if fav_cats else "")
        )
        fav_cat_names = [cat for cat, _ in cat_counter.most_common(2)]
    else:
        wishlist_info = "WISHLIST: Khách chưa có sách yêu thích."
        fav_cat_names = []

    # ── 3. Lịch sử xem gần đây ───────────────────────────────────────────────
    viewed_ids = request.session.get('recently_viewed', [])
    if viewed_ids:
        viewed_books = (
            Book.objects
            .filter(id__in=viewed_ids)
            .select_related('category')
        )
        viewed_map   = {b.id: b for b in viewed_books}
        viewed_lines = []
        for vid in viewed_ids:
            b = viewed_map.get(vid)
            if b:
                viewed_lines.append(
                    f"  • {b.title} – {b.author}"
                    f"{' [' + b.category.name + ']' if b.category else ''}"
                    f" – {b.price:,.0f}đ (ID:{b.id})"
                )
        viewed_info = "LỊCH SỬ XEM GẦN ĐÂY:\n" + "\n".join(viewed_lines)
    else:
        viewed_info = "LỊCH SỬ XEM: Chưa xem sách nào trong phiên này."

    # ── 4. Sách mới (90 ngày, còn hàng, tối đa 8) ────────────────────────────
    cutoff    = timezone.now().date() - timedelta(days=90)
    new_books = (
        Book.objects
        .filter(stock__gt=0, release_date__gte=cutoff)
        .select_related('category')
        .order_by('-release_date')[:8]
    )
    if new_books:
        new_books_info = "SÁCH MỚI (90 ngày gần đây, còn hàng):\n" + "\n".join(
            f"  • [ID:{b.id}] {b.title} – {b.author}"
            f"{' [' + b.category.name + ']' if b.category else ''}"
            f" – {b.price:,.0f}đ | Còn {b.stock} cuốn"
            for b in new_books
        )
    else:
        new_books_info = "SÁCH MỚI: Hiện chưa có sách mới trong 90 ngày."

    # ── 5. Sách bán chạy (tối đa 5) ──────────────────────────────────────────
    bestsellers = (
        Book.objects
        .filter(stock__gt=0)
        .select_related('category')
        .order_by('-sold_count')[:5]
    )
    bestseller_info = "SÁCH BÁN CHẠY:\n" + "\n".join(
        f"  • [ID:{b.id}] {b.title} – {b.author}"
        f"{' [' + b.category.name + ']' if b.category else ''}"
        f" – {b.price:,.0f}đ | Đã bán: {b.sold_count}"
        for b in bestsellers
    ) if bestsellers else "SÁCH BÁN CHẠY: Chưa có dữ liệu."

    # ── 6. Gợi ý cá nhân hoá theo sở thích danh mục ──────────────────────────
    if fav_cat_names:
        personal_books = (
            Book.objects
            .filter(stock__gt=0, category__name__in=fav_cat_names)
            .select_related('category')
            .order_by('-sold_count')[:5]
        )
        if personal_books:
            personal_info = (
                f"GỢI Ý CÁ NHÂN HÓA (theo sở thích {', '.join(fav_cat_names)}):\n"
                + "\n".join(
                    f"  • [ID:{b.id}] {b.title} – {b.author} – {b.price:,.0f}đ"
                    for b in personal_books
                )
            )
        else:
            personal_info = ""
    else:
        personal_info = ""

    # ── 7. Tất cả danh mục ───────────────────────────────────────────────────
    all_cats  = Category.objects.all()
    cat_info  = "DANH MỤC: " + ", ".join(c.name for c in all_cats)

    # ── 8. Xây dựng system prompt ─────────────────────────────────────────────
    system_prompt = f"""Bạn là DDC Books AI Bot – trợ lý tư vấn sách thông minh, thân thiện của DDC Books (Việt Nam).

=== THÔNG TIN CỬA HÀNG ===
- Địa chỉ: Số 9 Nguyễn Trãi, Hà Đông, Hà Nội
- Hotline: 094.152.7660 | Email: support@ddcbooks.com
- Giờ mở cửa: 08:00 – 22:00 (T2–CN)
- Đổi trả: 7 ngày, sản phẩm nguyên seal chưa qua sử dụng
- Vận chuyển nội thành HN: 1–2 ngày (miễn phí từ 250.000đ)
- Vận chuyển toàn quốc: 3–5 ngày (25.000–40.000đ)
- Thanh toán: COD hoặc chuyển khoản

=== KHÁCH HÀNG ĐANG CHAT ===
- Tên: {user_display}

{orders_info}

{wishlist_info}

{viewed_info}

=== DỮ LIỆU KHO SÁCH THỰC TẾ ===
{new_books_info}

{bestseller_info}

{personal_info}

{cat_info}

=== CÁCH TẠO LINK ĐẾN TRANG SÁCH ===
Khi đề cập một cuốn sách cụ thể có ID, hãy tạo link HTML như sau:
<a href="/book/ID/" style="color:#e67e22;font-weight:600;">Tên sách</a>
Ví dụ: <a href="/book/12/" style="color:#e67e22;font-weight:600;">Đắc Nhân Tâm</a>

=== NHIỆM VỤ ===
1. TRA ĐƠN HÀNG: Dùng dữ liệu đơn hàng ở trên, trả lời chính xác tình trạng, ngày đặt, sách trong đơn, đơn vị vận chuyển
2. GỢI Ý SÁCH: Ưu tiên sách còn hàng trong kho thực tế; cá nhân hoá theo wishlist và lịch sử xem; luôn kèm giá và link
3. TƯ VẤN: Trả lời câu hỏi về chính sách, vận chuyển, đổi trả, cách dùng website
4. PHÂN TÍCH SỞ THÍCH: Dùng wishlist và lịch sử xem để hiểu khách thích gì, gợi ý sách cùng danh mục

=== QUY TẮC TRẢ LỜI ===
- Thân thiện, nhiệt tình, ngắn gọn (tối đa 200 từ mỗi tin)
- Gọi khách bằng tên "{user_display}" khi phù hợp
- Dùng emoji hợp lý để gần gũi
- Khi gợi ý sách: luôn kèm tên tác giả, giá, và link HTML (dùng ID từ dữ liệu trên)
- Khi tra đơn hàng: đưa ra thông tin cụ thể (số đơn, trạng thái, ngày, sách)
- Không bịa thông tin sách ngoài danh sách đã cho
- Nếu câu hỏi vượt khả năng, đề xuất liên hệ nhân viên hoặc hotline 094.152.7660
- Luôn trả lời tiếng Việt trừ khi khách dùng ngôn ngữ khác"""

    # ── 9. Gọi Anthropic API ──────────────────────────────────────────────────
    api_key = getattr(django_settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return JsonResponse(
            {'error': 'Chưa cấu hình ANTHROPIC_API_KEY trong settings.py'},
            status=500
        )

    # Giới hạn history tối đa 20 lượt (40 items) để tránh payload quá lớn
    trimmed_history  = history[-40:] if len(history) > 40 else history
    messages_payload = trimmed_history + [{'role': 'user', 'content': user_message}]

    payload = json.dumps({
        'model'   : 'claude-sonnet-4-20250514',
        'max_tokens': 600,
        'system'  : system_prompt,
        'messages': messages_payload,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type'     : 'application/json',
            'x-api-key'        : api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        reply = (
            result.get('content', [{}])[0].get('text', '')
            or 'Xin lỗi, mình chưa có câu trả lời phù hợp. Bạn thử hỏi lại hoặc liên hệ nhân viên nhé! 🙏'
        )
        return JsonResponse({'reply': reply})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return JsonResponse({'error': f'Lỗi API: {e.code}', 'detail': error_body}, status=502)
    except urllib.error.URLError:
        return JsonResponse({'reply': 'Không kết nối được server AI. Vui lòng thử lại sau! 🙏'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
