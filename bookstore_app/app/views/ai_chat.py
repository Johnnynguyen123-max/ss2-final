import json
import urllib.request
import urllib.error
import re
import time
from collections import Counter
from datetime import timedelta

from django.http import StreamingHttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings as django_settings
from django.db.models import Q, F

from ..models import Book, Category, Order, OrderTracking, BotChatSession, BotChatMessage, PriceAlert


# ── HELPER: GET OR CREATE BOT SESSION ─────────────────────────────────────────
def get_bot_session(request):
    if request.user.is_authenticated:
        session, _ = BotChatSession.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        session, _ = BotChatSession.objects.get_or_create(session_key=session_key)
    return session


def perform_rag_search(user_message):
    cat_match = re.search(r'chủ\s+đề\s+([^\n\r\.\?]+)', user_message, re.IGNORECASE)
    if cat_match:
        cat_name = cat_match.group(1).strip()
        books = Book.objects.filter(category__name__icontains=cat_name).select_related('category')[:8]
        if books.exists():
            return books

    cleaned = re.sub(r'[^\w\s]', '', user_message.lower()).strip()
    words = cleaned.split()
    
    stop_words = {
        'có', 'sách', 'không', 'thể', 'loại', 'tìm', 'mua', 'cho', 'tôi', 'bạn',
        'nào', 'gì', 'bán', 'chạy', 'mới', 'nhất', 'ở', 'đâu', 'được', 'muốn',
        'giúp', 'cảm', 'ơn', 'hello', 'hi', 'bot', 'nhỉ', 'nhé', 'đi', 'với', 'cửa', 'hàng'
    }
    keywords = [w for w in words if w not in stop_words and len(w) >= 2]
    
    if not keywords:
        return Book.objects.none()
        
    query = Q()
    for kw in keywords[:3]:
        query |= Q(title__icontains=kw) | Q(author__icontains=kw) | Q(category__name__icontains=kw)
        
    return Book.objects.filter(query).select_related('category')[:8]


# ── HELPER: MOCK AI RESPONSE GENERATOR FOR OFFLINE TESTING ──────────────────
def get_mock_ai_response(user_message, user, recent_orders, rag_books, new_books, bestsellers):
    lower = user_message.lower()
    user_name = user.get_full_name() or user.username if user else "khách hàng"
    
    # 1. Search books (RAG)
    if rag_books.exists():
        books_list = []
        for b in rag_books[:3]:
            books_list.append(f'- <a href="/book/{b.id}/" style="color:#e67e22;font-weight:600;">{b.title}</a> (Tác giả: {b.author}, Giá: {b.price:,.0f}đ)')
        
        reply = f"Chào {user_name}! Dưới đây là các sách trùng khớp với tìm kiếm của bạn tại DDC Books:\n\n" + "\n".join(books_list) + "\n\nBạn có thể nhấn vào nút 'Mua ngay' dưới mỗi thẻ sách bên dưới để thêm trực tiếp vào giỏ hàng nhé! 😊\n\n[SUGGESTIONS: \"Tìm sách khác\", \"Sách bán chạy nhất\", \"Chính sách đổi trả\"]"
        return reply

    # 2. Track order
    if 'đơn' in lower or 'order' in lower or '#' in lower:
        order_match = re.search(r'#(\d+)', user_message)
        if order_match:
            oid = order_match.group(1)
            try:
                if user:
                    o = Order.objects.get(id=oid, user=user)
                else:
                    o = Order.objects.get(id=oid) # Guest mockup matching
                
                status_desc = o.get_status_display()
                reply = f"Dạ, mình đã tìm thấy thông tin đơn hàng #{o.id} của {user_name}!\n\nĐơn hàng đặt ngày {o.created_at.strftime('%d/%m/%Y')} có tổng trị giá {o.total_price:,.0f}đ đang ở trạng thái <strong>{status_desc}</strong>.\n\nThông tin vận chuyển chi tiết đã hiển thị ở thẻ hành trình phía dưới nhé! 🚚\n\n[SUGGESTIONS: \"Sách mới về gần đây\", \"Chính sách đổi trả\", \"Liên hệ nhân viên\"]"
                return reply
            except Order.DoesNotExist:
                pass
        
        if recent_orders:
            o = recent_orders[0]
            reply = f"Dạ, đây là đơn hàng gần nhất của {user_name} trên hệ thống:\n\nĐơn hàng <strong>#{o.id}</strong> đặt ngày {o.created_at.strftime('%d/%m/%Y')} với tổng giá trị {o.total_price:,.0f}đ. Trạng thái hiện tại: <strong>{o.get_status_display()}</strong>.\n\nBạn xem thông tin đơn hàng ở bên dưới để biết chi tiết hành trình vận chuyển nhé! 📦\n\n[SUGGESTIONS: \"Sách bán chạy nhất\", \"Chính sách đổi trả\", \"Địa chỉ cửa hàng\"]"
            return reply
        else:
            # Check if guest specifies order & phone
            guest_track_match = re.search(r'(\d+).*(0\d{9,10})', user_message) or re.search(r'(0\d{9,10}).*(\d+)', user_message)
            if guest_track_match:
                groups = guest_track_match.groups()
                oid = groups[0] if len(groups[0]) < 8 else groups[1]
                phone = groups[1] if len(groups[0]) < 8 else groups[0]
                try:
                    o = Order.objects.get(id=oid, phone=phone)
                    reply = f"Cảm ơn bạn! Mình đã xác nhận đơn hàng #{o.id} khớp với số điện thoại {phone}.\n\nTrạng thái đơn hàng: <strong>{o.get_status_display()}</strong>.\n\nThông tin chi tiết đã được tải bên dưới! 🚚\n\n[TRACK_GUEST_ORDER: order_id={o.id}, phone={phone}]\n[SUGGESTIONS: \"Sách mới về\", \"Chính sách ship\", \"Mua sách hay\"]"
                    return reply
                except Order.DoesNotExist:
                    pass
            
            reply = f"Chào {user_name}! Để tra cứu đơn hàng vãng lai, bạn vui lòng nhắn tin theo cú pháp: <strong>[Mã đơn hàng] kèm [Số điện thoại]</strong> đặt hàng nhé! (Ví dụ: Tra cứu đơn 12 sđt 0912345678)\n\n[SUGGESTIONS: \"Sách bán chạy\", \"Địa chỉ cửa hàng\", \"Chính sách đổi trả\"]"
            return reply

    # 3. Price alert
    if 'nhắc' in lower or 'báo giá' in lower or 'alert' in lower or 'chuông' in lower or 'giảm' in lower:
        price_match = re.search(r'(\d+)\s*(k|đ|đồng|nghìn)', lower)
        target_price = 80000
        if price_match:
            val = int(price_match.group(1))
            if val < 1000:
                target_price = val * 1000
            else:
                target_price = val
        
        if rag_books.exists():
            b = rag_books[0]
        else:
            b = Book.objects.first()
            
        if b:
            reply = f"Vâng! Mình đã thiết lập chuông cảnh báo giá cho cuốn sách <strong>{b.title}</strong>. Mình sẽ thông báo ngay cho {user_name} trong cửa sổ chat khi giá cuốn sách này giảm xuống dưới {target_price:,.0f}đ! 🔔\n\n[SET_PRICE_ALERT: book_id={b.id}, target_price={target_price}]\n[SUGGESTIONS: \"Tìm sách khác\", \"Giỏ hàng của tôi\", \"Chính sách đổi trả\"]"
            return reply

    # 4. Book recommendations
    if 'gợi ý' in lower or 'recommend' in lower or 'khuyên' in lower or 'hay' in lower or 'tư vấn' in lower:
        books_list = []
        source_books = new_books if new_books.exists() else bestsellers
        for b in source_books[:3]:
            books_list.append(f'- <a href="/book/{b.id}/" style="color:#e67e22;font-weight:600;">{b.title}</a> (Giá: {b.price:,.0f}đ)')
        
        reply = f"Chào {user_name}! Dưới đây là một số cuốn sách hay nổi bật tại DDC Books dành cho bạn:\n\n" + "\n".join(books_list) + "\n\nCác cuốn sách này đều có sẵn trong kho, bạn có thể nhấn mua ngay ở các thẻ sách bên dưới nhé! 📚\n\n[SUGGESTIONS: \"Sách bán chạy nhất\", \"Tìm sách văn học\", \"Chính sách đổi trả\"]"
        return reply

    # 5. New books
    if 'mới' in lower or 'new' in lower:
        if new_books.exists():
            books_list = []
            for b in new_books[:3]:
                books_list.append(f'- <a href="/book/{b.id}/" style="color:#e67e22;font-weight:600;">{b.title}</a> ({b.price:,.0f}đ)')
            reply = f"Dạ, đây là danh sách sách mới cập bến tại cửa hàng DDC Books:\n\n" + "\n".join(books_list) + "\n\nMời bạn xem qua! 🆕\n\n[SUGGESTIONS: \"Sách bán chạy nhất\", \"Tư vấn sách hay\", \"Địa chỉ shop\"]"
        else:
            reply = "Hiện cửa hàng chưa cập nhật sách mới trong 90 ngày qua. Bạn xem qua các sách bán chạy bên dưới nhé! 😊\n\n[SUGGESTIONS: \"Sách bán chạy\", \"Địa chỉ shop\", \"Chính sách đổi trả\"]"
        return reply

    # 6. Bestsellers
    if 'bán chạy' in lower or 'hot' in lower or 'chạy nhất' in lower:
        if bestsellers.exists():
            books_list = []
            for b in bestsellers[:3]:
                books_list.append(f'- <a href="/book/{b.id}/" style="color:#e67e22;font-weight:600;">{b.title}</a> (Đã bán: {b.sold_count})')
            reply = f"Chào {user_name}! Đây là các tựa sách đang bán chạy nhất và được yêu thích tại DDC Books:\n\n" + "\n".join(books_list) + "\n\nBạn có muốn tìm hiểu thêm về cuốn nào không? 🔥\n\n[SUGGESTIONS: \"Sách mới về\", \"Gợi ý sách hay\", \"Liên hệ nhân viên\"]"
        else:
            reply = "Hiện chưa có dữ liệu sách bán chạy. Bạn xem qua sách mới cập nhật bên dưới nhé! 😊\n\n[SUGGESTIONS: \"Sách mới về\", \"Địa chỉ shop\", \"Chính sách đổi trả\"]"
        return reply

    # Fallback greeting
    reply = f"Chào {user_name}! Mình là DDC Books AI Bot 🤖\nMình có thể hỗ trợ bạn tư vấn sách hay, cập nhật sách bán chạy, tra cứu hành trình đơn hàng, cài đặt thông báo giá hoặc chính sách của cửa hàng.\n\nBạn cần mình hỗ trợ thông tin gì hôm nay? 😊\n\n[SUGGESTIONS: \"Gợi ý sách hay\", \"Tra cứu đơn hàng\", \"Địa chỉ và giờ mở cửa\"]"
    return reply


# ── AI CHATBOT STREAMING (SSE) ────────────────────────────────────────────────
@require_POST
def chat_bot_stream(request):
    # Rate limit: 1 request per second
    last_call = request.session.get('bot_last_call', 0)
    now_ts = timezone.now().timestamp()
    if now_ts - last_call < 1:
        return JsonResponse({'error': 'Vui lòng chờ một chút trước khi gửi tiếp.'}, status=429)
    request.session['bot_last_call'] = now_ts

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = data.get('message', '').strip()
    if not user_message:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)

    bot_session = get_bot_session(request)

    # 1. Save user message to database
    BotChatMessage.objects.create(session=bot_session, role='user', content=user_message)

    # 2. Gather context
    user = request.user if request.user.is_authenticated else None
    user_display = user.get_full_name() or user.username if user else "Khách hàng"

    # Orders Context
    if user:
        recent_orders = (
            Order.objects
            .filter(user=user)
            .prefetch_related('items__book', 'trackings')
            .order_by('-created_at')[:5]
        )
    else:
        guest_order_ids = request.session.get('guest_orders', [])
        recent_orders = (
            Order.objects
            .filter(id__in=guest_order_ids)
            .prefetch_related('items__book', 'trackings')
            .order_by('-created_at')[:5]
        )

    if recent_orders:
        order_lines = []
        for o in recent_orders:
            items_str = ", ".join(
                f"{i.book.title} (x{i.quantity}, {i.price:,.0f}đ)"
                for i in o.items.all()
            )
            last_track = o.trackings.order_by('-created_at').first()
            track_msg = f" | Trạng thái: {last_track.message}" if last_track else ""
            ship_info = f" | Ship: {o.shipping_unit}" if o.shipping_unit else ""
            order_lines.append(
                f"  • Đơn #{o.id} [{o.get_status_display()}]{ship_info}"
                f" | {o.created_at.strftime('%d/%m/%Y')} | Tổng: {o.total_price:,.0f}đ"
                f" | Sách: {items_str}{track_msg}"
            )
        orders_info = "ĐƠN HÀNG GẦN ĐÂY:\n" + "\n".join(order_lines)
    else:
        orders_info = "ĐƠN HÀNG: Khách chưa có đơn hàng nào."

    # Wishlist Context
    if user:
        wishlist_qs = Book.objects.filter(wishlist=user).select_related('category')[:10]
    else:
        wishlist_qs = Book.objects.none()

    if wishlist_qs:
        wishlist_lines = [
            f"  • {b.title} – {b.author} – {b.price:,.0f}đ"
            for b in wishlist_qs
        ]
        cat_counter = Counter(b.category.name for b in wishlist_qs if b.category)
        fav_cats = ", ".join(f"{cat} ({cnt} cuốn)" for cat, cnt in cat_counter.most_common(3))
        wishlist_info = "WISHLIST:\n" + "\n".join(wishlist_lines) + (f"\n  → Sở thích: {fav_cats}" if fav_cats else "")
        fav_cat_names = [cat for cat, _ in cat_counter.most_common(2)]
    else:
        wishlist_info = "WISHLIST: Không có dữ liệu."
        fav_cat_names = []

    # Viewed Books
    viewed_ids = request.session.get('recently_viewed', [])
    if viewed_ids:
        viewed_books = Book.objects.filter(id__in=viewed_ids).select_related('category')
        viewed_map = {b.id: b for b in viewed_books}
        viewed_lines = []
        for vid in viewed_ids:
            b = viewed_map.get(vid)
            if b:
                viewed_lines.append(f"  • [ID:{b.id}] {b.title} – {b.price:,.0f}đ")
        viewed_info = "LỊCH SỬ XEM GẦN ĐÂY:\n" + "\n".join(viewed_lines)
    else:
        viewed_info = "LỊCH SỬ XEM: Chưa có dữ liệu."

    # RAG search Context
    rag_books = perform_rag_search(user_message)
    if rag_books.exists():
        rag_lines = [
            f"  • [ID:{b.id}] {b.title} – Tác giả: {b.author} – Giá: {b.price:,.0f}đ"
            f" | Tồn kho: {b.stock} | Thể loại: {b.category.name if b.category else 'N/A'}"
            for b in rag_books
        ]
        rag_info = "KẾT QUẢ TÌM KIẾM SÁCH LIÊN QUAN:\n" + "\n".join(rag_lines)
    else:
        rag_info = "KẾT QUẢ TÌM KIẾM SÁCH LIÊN QUAN: Không tìm thấy sách trùng khớp trực tiếp."

    # Store general books
    cutoff = timezone.now().date() - timedelta(days=90)
    new_books = Book.objects.filter(stock__gt=0, release_date__gte=cutoff).select_related('category').order_by('-release_date')[:6]
    new_books_info = "SÁCH MỚI VỀ:\n" + "\n".join(
        f"  • [ID:{b.id}] {b.title} – {b.author} – {b.price:,.0f}đ"
        for b in new_books
    ) if new_books else "SÁCH MỚI VỀ: Không có."

    bestsellers = Book.objects.filter(stock__gt=0).select_related('category').order_by('-sold_count')[:5]
    bestseller_info = "SÁCH BÁN CHẠY:\n" + "\n".join(
        f"  • [ID:{b.id}] {b.title} – {b.author} – {b.price:,.0f}đ"
        for b in bestsellers
    ) if bestsellers else "SÁCH BÁN CHẠY: Không có."

    all_cats = Category.objects.all()
    cat_info = "DANH MỤC CỬA HÀNG: " + ", ".join(c.name for c in all_cats)

    api_key = getattr(django_settings, 'ANTHROPIC_API_KEY', '')

    # Yield stream
    def sse_generator():
        # FALLBACK: If ANTHROPIC_API_KEY is empty, stream the mock AI response locally
        if not api_key:
            mock_reply = get_mock_ai_response(user_message, user, recent_orders, rag_books, new_books, bestsellers)
            full_text = mock_reply
            
            # Stream mock response chunk by chunk to simulate AI response speed
            chunk_size = 6
            for idx in range(0, len(mock_reply), chunk_size):
                chunk = mock_reply[idx:idx+chunk_size]
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                time.sleep(0.015)
        else:
            # 3. System Prompt
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
- Phân loại: {"Thành viên" if user else "Khách vãng lai"}

{orders_info}

{wishlist_info}

{viewed_info}

=== DỮ LIỆU KHO SÁCH HỆ THỐNG ===
{rag_info}

{new_books_info}

{bestseller_info}

{cat_info}

=== QUY TẮC RENDER LINK SÁCH ===
Khi nói về sách có ID, bắt buộc tạo thẻ link HTML:
<a href="/book/ID/" style="color:#e67e22;font-weight:600;">Tên sách</a>
Ví dụ: <a href="/book/12/" style="color:#e67e22;font-weight:600;">Đắc Nhân Tâm</a>

=== QUY TẮC TRA ĐƠN GUEST ===
Nếu khách hàng là khách vãng lai và muốn tra đơn hàng (không thuộc lịch sử đơn hàng ở trên):
1. Yêu cầu khách cung cấp số điện thoại đặt hàng và mã đơn.
2. Khi khách đã cung cấp đầy đủ mã đơn (ví dụ: 15) và số điện thoại (ví dụ: 0912345678), hãy kết luận bằng một dòng đặc biệt để backend xử lý:
[TRACK_GUEST_ORDER: order_id=15, phone=0912345678]

=== QUY TẮC ĐẶT NHẮC NHỞ / CẢNH BÁO GIÁ ===
Nếu khách hàng yêu cầu thông báo khi một cuốn sách giảm giá dưới một mức giá mục tiêu:
1. Xác định ID sách và mức giá mục tiêu.
2. Thêm thẻ đặc biệt này ở cuối câu trả lời của bạn:
[SET_PRICE_ALERT: book_id=ID, target_price=PRICE]
Ví dụ: [SET_PRICE_ALERT: book_id=12, target_price=75000]

=== QUY TẮC RENDER CHIPS GỢI Ý (OBLIGATORY) ===
Sau mỗi câu trả lời, hãy ĐƯA RA 2 ĐẾN 3 gợi ý tiếp theo phù hợp với ngữ cảnh hội thoại dưới định dạng thẻ đặc biệt ở cuối cùng câu trả lời:
[SUGGESTIONS: "Câu gợi ý 1", "Câu gợi ý 2", "Câu gợi ý 3"]
Ví dụ: [SUGGESTIONS: "Gợi ý sách lập trình khác", "Mã giảm giá hôm nay", "Chính sách ship toàn quốc"]

=== QUY TẮC TRẢ LỜI ===
- Thân thiện, nhiệt tình, ngắn gọn (tối đa 150 từ mỗi phản hồi).
- Tuyệt đối không bịa đặt sách không có trong hệ thống hoặc kết quả tìm kiếm ở trên.
- Trả lời bằng tiếng Việt."""

            # 4. Read history
            history_messages = bot_session.messages.all().order_by('-created_at')[:10]
            history_messages = list(reversed(history_messages))
            
            messages_payload = []
            for msg in history_messages:
                if msg.role == 'user' and msg.content == user_message:
                    continue
                messages_payload.append({
                    'role': msg.role,
                    'content': msg.content
                })
            messages_payload.append({'role': 'user', 'content': user_message})

            payload = json.dumps({
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 600,
                'system': system_prompt,
                'messages': messages_payload,
                'stream': True
            }).encode('utf-8')

            req = urllib.request.Request(
                'https://api.anthropic.com/v1/messages',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                },
                method='POST'
            )

            full_text = ""
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    buffer = ""
                    for byte_chunk in resp:
                        buffer += byte_chunk.decode('utf-8')
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("data:"):
                                data_str = line[5:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    event_data = json.loads(data_str)
                                    if event_data.get("type") == "content_block_delta":
                                        text = event_data.get("delta", {}).get("text", "")
                                        if text:
                                            full_text += text
                                            yield f"data: {json.dumps({'chunk': text})}\n\n"
                                except Exception:
                                    pass
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                yield f"data: {json.dumps({'error': f'Lỗi API: {e.code}', 'detail': err_body})}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

        # --- STREAM FINISHED, POST-PROCESSING ---
        # 1. Parse suggestions
        suggestions = []
        suggestion_match = re.search(r'\[SUGGESTIONS:\s*(.*?)\]', full_text)
        cleaned_text = full_text
        if suggestion_match:
            try:
                suggestions_str = suggestion_match.group(1)
                suggestions = json.loads(f"[{suggestions_str}]")
            except Exception:
                suggestions = [s.strip().strip('"\'') for s in suggestion_match.group(1).split(',')]
            cleaned_text = cleaned_text[:suggestion_match.start()].strip()

        # 2. Parse price alert commands
        alert_match = re.search(r'\[SET_PRICE_ALERT:\s*book_id=(\d+),\s*target_price=(\d+)\]', cleaned_text)
        alert_created = False
        alert_book_title = ""
        if alert_match:
            try:
                bid = int(alert_match.group(1))
                price = int(alert_match.group(2))
                book = Book.objects.get(id=bid)
                PriceAlert.objects.create(
                    user=user,
                    session_key=None if user else bot_session.session_key,
                    book=book,
                    target_price=price
                )
                alert_created = True
                alert_book_title = book.title
            except Exception:
                pass
            cleaned_text = re.sub(r'\[SET_PRICE_ALERT:\s*book_id=\d+,\s*target_price=\d+\]', '', cleaned_text).strip()

        # 3. Parse track guest order commands
        guest_track_match = re.search(r'\[TRACK_GUEST_ORDER:\s*order_id=(\d+),\s*phone=([\d\+\s]+)\]', cleaned_text)
        if guest_track_match:
            try:
                oid = int(guest_track_match.group(1))
                phone = guest_track_match.group(2).strip()
                if Order.objects.filter(id=oid, phone=phone).exists():
                    guest_orders = request.session.get('guest_orders', [])
                    if oid not in guest_orders:
                        guest_orders.append(oid)
                        request.session['guest_orders'] = guest_orders
                        request.session.modified = True
            except Exception:
                pass
            cleaned_text = re.sub(r'\[TRACK_GUEST_ORDER:\s*order_id=\d+,\s*phone=[\d\+\s]+\]', '', cleaned_text).strip()

        # 4. Parse book recommendations
        book_ids = list(set([int(bid) for bid in re.findall(r'/book/(\d+)/', cleaned_text)]))
        books_data = []
        for bid in book_ids:
            try:
                b = Book.objects.get(id=bid)
                books_data.append({
                    'id': b.id,
                    'title': b.title,
                    'author': b.author,
                    'price': float(b.price),
                    'image_url': b.image.url if b.image else '/static/app/images/default_book.png',
                    'stock': b.stock,
                    'category': b.category.name if b.category else '',
                })
            except Book.DoesNotExist:
                pass

        # 5. Parse orders (both guest and member)
        order_ids = list(set([int(oid) for oid in re.findall(r'#(\d+)', cleaned_text)]))
        orders_data = []
        for oid in order_ids:
            try:
                if user:
                    o = Order.objects.get(id=oid, user=user)
                else:
                    guest_orders = request.session.get('guest_orders', [])
                    if oid in guest_orders:
                        o = Order.objects.get(id=oid)
                    else:
                        continue

                last_track = o.trackings.order_by('-created_at').first()
                orders_data.append({
                    'id': o.id,
                    'status': o.status,
                    'status_display': o.get_status_display(),
                    'total_price': float(o.total_price),
                    'created_at': o.created_at.strftime('%d/%m/%Y'),
                    'shipping_unit': o.shipping_unit or 'Chưa có thông tin',
                    'last_tracking': last_track.message if last_track else 'Chờ cập nhật hành trình'
                })
            except Order.DoesNotExist:
                pass

        # 6. Save AI message in database
        bot_msg = BotChatMessage.objects.create(session=bot_session, role='assistant', content=cleaned_text)

        # 7. Yield final metadata chunk
        metadata = {
            'message_id': bot_msg.id,
            'books': books_data,
            'orders': orders_data,
            'suggestions': suggestions,
            'alert_created': alert_created,
            'alert_book_title': alert_book_title,
        }
        yield f"data: {json.dumps({'metadata': metadata})}\n\n"

    response = StreamingHttpResponse(sse_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── AI CHATBOT HISTORY ────────────────────────────────────────────────────────
@require_GET
def chat_bot_history(request):
    bot_session = get_bot_session(request)
    messages = bot_session.messages.all().order_by('created_at')
    
    msg_list = []
    for m in messages:
        books_data = []
        orders_data = []
        
        if m.role == 'assistant':
            book_ids = list(set([int(bid) for bid in re.findall(r'/book/(\d+)/', m.content)]))
            for bid in book_ids:
                try:
                    b = Book.objects.get(id=bid)
                    books_data.append({
                        'id': b.id,
                        'title': b.title,
                        'author': b.author,
                        'price': float(b.price),
                        'image_url': b.image.url if b.image else '/static/app/images/default_book.png',
                        'stock': b.stock,
                        'category': b.category.name if b.category else '',
                    })
                except Book.DoesNotExist:
                    pass

            order_ids = list(set([int(oid) for oid in re.findall(r'#(\d+)', m.content)]))
            user = request.user if request.user.is_authenticated else None
            for oid in order_ids:
                try:
                    if user:
                        o = Order.objects.get(id=oid, user=user)
                    else:
                        guest_orders = request.session.get('guest_orders', [])
                        if oid in guest_orders:
                            o = Order.objects.get(id=oid)
                        else:
                            continue
                    
                    last_track = o.trackings.order_by('-created_at').first()
                    orders_data.append({
                        'id': o.id,
                        'status': o.status,
                        'status_display': o.get_status_display(),
                        'total_price': float(o.total_price),
                        'created_at': o.created_at.strftime('%d/%m/%Y'),
                        'shipping_unit': o.shipping_unit or 'Chưa có thông tin',
                        'last_tracking': last_track.message if last_track else 'Chờ cập nhật hành trình'
                    })
                except Order.DoesNotExist:
                    pass

        msg_list.append({
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.strftime('%H:%M'),
            'rating': m.rating,
            'books': books_data,
            'orders': orders_data,
        })
        
    return JsonResponse({'messages': msg_list})


# ── AI CHATBOT FEEDBACK (LIKE/DISLIKE) ────────────────────────────────────────
@require_POST
def chat_bot_feedback(request):
    bot_session = get_bot_session(request)
    try:
        data = json.loads(request.body)
        message_id = int(data.get('message_id'))
        rating = int(data.get('rating'))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'Invalid arguments'}, status=400)

    try:
        msg = BotChatMessage.objects.get(id=message_id, session=bot_session, role='assistant')
        msg.rating = rating
        msg.save(update_fields=['rating'])
        return JsonResponse({'success': True, 'rating': msg.rating})
    except BotChatMessage.DoesNotExist:
        return JsonResponse({'error': 'Tin nhắn không tồn tại'}, status=404)
