import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Case, When, Avg
from django.views.decorators.http import require_POST, require_GET
from datetime import datetime, timedelta

from .models import (
    Profile, Book, Category, Order, OrderItem,
    Comment, OrderTracking, ChatSession, ChatMessage,
    FlashSaleConfig,
)
from .forms import UserUpdateForm, ProfileUpdateForm


# ── TRANG CHỦ ────────────────────────────────────────────────────────────────
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    filter_type = request.GET.get('filter')
    price_range = request.GET.get('price_range')
    year = request.GET.get('year')

    books = Book.objects.all()
    current_year = datetime.now().year
    year_choices = range(current_year, current_year - 6, -1)

    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    if category_id:
        books = books.filter(category_id=category_id)

    if filter_type == 'new':
        last_90_days = timezone.now() - timedelta(days=90)
        books = books.filter(release_date__gte=last_90_days)
    elif filter_type == 'sale':
        books = books.order_by('price')
    elif filter_type == 'bestseller':
        books = books.order_by('release_date')  # TODO: đổi sang -sold_count sau khi chạy migrate
    elif filter_type == 'combo':
        books = books.order_by('-release_date')

    if price_range:
        if price_range == "0-100000":
            books = books.filter(price__lt=100000)
        elif price_range == "100000-300000":
            books = books.filter(price__gte=100000, price__lte=300000)
        elif price_range == "300000-max":
            books = books.filter(price__gt=300000)

    if year:
        if year == 'older':
            books = books.filter(release_date__year__lt=current_year - 5)
        else:
            books = books.filter(release_date__year=year)

    books = books.order_by('-release_date')

    favorite_book_ids = []
    if request.user.is_authenticated:
        favorite_book_ids = list(
            Book.objects.filter(wishlist=request.user).values_list('id', flat=True)
        )

    categories = Category.objects.all()

    viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed_books = []
    if viewed_ids:
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(viewed_ids)])
        recently_viewed_books = Book.objects.filter(id__in=viewed_ids).order_by(preserved)

    # Số liệu thực cho hero stats
    avg_rating = Comment.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    new_books_count = Book.objects.filter(
        release_date__gte=timezone.now().date() - timedelta(days=90)
    ).count()

    # ── Flash sale ────────────────────────────────────────────
    flash_config   = FlashSaleConfig.get_config()
    flash_active   = flash_config.is_sale_now()
    flash_discount = flash_config.discount_percent if flash_active else 0

    # Nếu đang sale, filter=sale sẽ hiển thị toàn bộ sách (đã giảm hết)
    if filter_type == 'sale' and flash_active:
        books = Book.objects.all().order_by('-release_date')
        if query:
            books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    context = {
        'books': books,
        'categories': categories,
        'year_choices': year_choices,
        'favorite_book_ids': favorite_book_ids,
        'query': query,
        'filter_type': filter_type,
        'recently_viewed_books': recently_viewed_books,
        'selected_price': price_range,
        'selected_year': year,
        'avg_rating': avg_rating,
        'new_books_count': new_books_count,
        # Flash sale
        'flash_active': flash_active,
        'flash_discount': flash_discount,
        'flash_config': flash_config,
    }
    return render(request, 'app/home.html', context)


# ── ĐĂNG KÝ ──────────────────────────────────────────────────────────────────
def signup(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            if User.objects.filter(username=email).exists():
                return render(request, 'app/signup.html', {'error': 'Email này đã được đăng ký rồi!'})

            user = User.objects.create_user(
                username=email, email=email, password=password, first_name=full_name
            )
            Profile.objects.get_or_create(user=user)
            messages.success(request, 'Đăng ký thành công! Mời bạn đăng nhập.')
            return redirect('login')
        else:
            return render(request, 'app/signup.html', {'error': 'Mật khẩu xác nhận không khớp'})

    return render(request, 'app/signup.html')


# ── ĐĂNG NHẬP ────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        email_input = request.POST.get('username')
        password_input = request.POST.get('password')

        try:
            user = User.objects.get(username=email_input)
            if user.check_password(password_input):
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                if user.groups.filter(name='Staff').exists() or user.is_superuser:
                    return redirect('manage_orders')
                return redirect('home')
            else:
                return render(request, 'app/login.html', {'error': 'Mật khẩu không chính xác'})
        except User.DoesNotExist:
            return render(request, 'app/login.html', {'error': 'Tài khoản Email này không tồn tại'})

    return render(request, 'app/login.html')


# ── ĐĂNG XUẤT ────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('home')


# ── HỒ SƠ ────────────────────────────────────────────────────────────────────
@login_required
def profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Hồ sơ đã được cập nhật!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=user_profile)

    return render(request, 'app/profile.html', {'u_form': u_form, 'p_form': p_form})


# ── WISHLIST ──────────────────────────────────────────────────────────────────
@login_required
def toggle_wishlist(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            if not book_id:
                return JsonResponse({'status': 'error', 'message': 'Thiếu ID sách'}, status=400)

            book = get_object_or_404(Book, id=book_id)
            if book.wishlist.filter(id=request.user.id).exists():
                book.wishlist.remove(request.user)
                action, is_favorite = 'removed', False
            else:
                book.wishlist.add(request.user)
                action, is_favorite = 'added', True

            return JsonResponse({'status': 'success', 'action': action, 'is_favorite': is_favorite})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'}, status=405)


@login_required
def wishlist_list(request):
    favorite_books = Book.objects.filter(wishlist=request.user).order_by('-id')
    return render(request, 'app/wishlist.html', {
        'books': favorite_books,
        'title': 'Sách yêu thích của tôi'
    })


# ── SÁCH ─────────────────────────────────────────────────────────────────────
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    related_books = Book.objects.filter(category=book.category).exclude(id=book_id)[:5]

    if 'recently_viewed' not in request.session:
        request.session['recently_viewed'] = []
    recently_viewed = request.session['recently_viewed']
    if book_id in recently_viewed:
        recently_viewed.remove(book_id)
    recently_viewed.insert(0, book_id)
    request.session['recently_viewed'] = recently_viewed[:6]
    request.session.modified = True

    comments = book.comments.all().order_by('-created_at')
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = book.wishlist.filter(id=request.user.id).exists()

    return render(request, 'app/book_detail.html', {
        'book': book,
        'comments': comments,
        'is_favorite': is_favorite,
        'related_books': related_books,
    })


def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    starts_with = Book.objects.filter(title__istartswith=query)
    contains = Book.objects.filter(
        Q(title__icontains=query) | Q(author__icontains=query)
    ).exclude(id__in=starts_with.values_list('id', flat=True))

    books = (list(starts_with) + list(contains))[:5]
    results = []
    for book in books:
        img_url = book.image.url if book.image else '/static/app/images/default.jpg'
        results.append({
            'id': book.id,
            'title': book.title[:50] + '...' if len(book.title) > 50 else book.title,
            'author': book.author,
            'price': "{:,.0f}₫".format(book.price) if book.price else "Free",
            'image': img_url,
        })
    return JsonResponse({'results': results})


# ── GIỎ HÀNG ─────────────────────────────────────────────────────────────────
def add_to_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        quantity = int(request.POST.get('quantity', 1))
        str_id = str(book_id)
        cart[str_id] = cart.get(str_id, 0) + quantity
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({'status': 'success', 'total_items': sum(cart.values())})
    return JsonResponse({'status': 'error'}, status=400)


def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for book_id, quantity in cart.items():
        book = get_object_or_404(Book, id=book_id)
        subtotal = book.price * quantity
        total_price += subtotal
        cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})
    return render(request, 'app/cart.html', {'cart_items': cart_items, 'total_price': total_price})


def update_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        action = request.POST.get('action')
        str_id = str(book_id)
        if str_id in cart:
            if action == 'increase':
                cart[str_id] += 1
            elif action == 'decrease':
                cart[str_id] = max(1, cart[str_id] - 1)
            request.session['cart'] = cart
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


def remove_from_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        str_id = str(book_id)
        if str_id in cart:
            del cart[str_id]
            request.session['cart'] = cart
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# ── CHECKOUT ──────────────────────────────────────────────────────────────────
@login_required
def checkout(request):
    cart_session = request.session.get('cart', {})
    if not cart_session:
        messages.warning(request, "Giỏ hàng của bạn đang trống!")
        return redirect('cart_detail')

    cart_items = []
    total_bill = 0
    for book_id, quantity in cart_session.items():
        book = get_object_or_404(Book, id=book_id)
        subtotal = book.price * quantity
        total_bill += subtotal
        cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})

    user_profile = getattr(request.user, 'profile', None)
    initial_full_name = f"{request.user.last_name} {request.user.first_name}".strip() or request.user.username
    initial_phone = user_profile.phone if user_profile else ""
    initial_address = user_profile.address if user_profile else ""

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        if not all([full_name, phone, address]):
            messages.error(request, "Vui lòng điền đầy đủ thông tin giao hàng!")
            return render(request, 'app/checkout.html', {
                'items': cart_items, 'total_bill': total_bill,
                'full_name': full_name, 'phone': phone, 'address': address
            })

        if not re.match(r"^(0[35789])[0-9]{8}$", phone):
            messages.error(request, "Số điện thoại không đúng định dạng Việt Nam!")
            return render(request, 'app/checkout.html', {
                'items': cart_items, 'total_bill': total_bill,
                'full_name': full_name, 'phone': phone, 'address': address
            })

        order = Order.objects.create(
            user=request.user, full_name=full_name,
            phone=phone, address=address, total_price=total_bill
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order, book=item['book'],
                quantity=item['quantity'], price=item['book'].price
            )

        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, f"Chúc mừng {full_name}, đơn hàng đã được hệ thống tiếp nhận!")
        return render(request, 'app/checkout.html', {'items': [], 'total_bill': 0})

    return render(request, 'app/checkout.html', {
        'items': cart_items, 'total_bill': total_bill,
        'full_name': initial_full_name, 'phone': initial_phone, 'address': initial_address
    })


# ── BÌNH LUẬN ────────────────────────────────────────────────────────────────
@login_required
def post_comment(request, book_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        rating = request.POST.get('rating', 5)
        if content:
            book = get_object_or_404(Book, id=book_id)
            Comment.objects.create(book=book, user=request.user, content=content, rating=int(rating))
    return redirect('book_detail', book_id=book_id)


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    book_id = comment.book.id
    if request.user == comment.user or request.user.is_superuser:
        comment.delete()
        messages.success(request, "Đã xóa bình luận thành công.")
    else:
        messages.error(request, "Bạn không có quyền xóa bình luận này.")
    return redirect('book_detail', book_id=book_id)


# ── ĐƠN HÀNG (KHÁCH) ─────────────────────────────────────────────────────────
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app/order_history.html', {'orders': orders})


@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.delete()
    messages.success(request, "Đã xóa đơn hàng thành công!")
    return redirect('order_history')


@login_required
def update_order_info(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.full_name = request.POST.get('full_name')
        order.phone = request.POST.get('phone')
        order.address = request.POST.get('address')
        order.save()
        messages.success(request, "Đã cập nhật thông tin đơn hàng!")
    return redirect('order_history')


@login_required
def order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'app/order_tracking.html', {
        'order': order,
        'order_items': order.items.all(),
    })


@login_required
def confirm_received(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Shipped':
        order.status = 'Received'
        order.save()
        OrderTracking.objects.create(
            order=order, status='Received',
            message='Giao hàng thành công. Người mua đã xác nhận nhận hàng.'
        )
    return redirect('order_history')


# ── ĐƠN HÀNG (STAFF) ─────────────────────────────────────────────────────────
def is_staff(user):
    return user.groups.filter(name='Staff').exists() or user.is_superuser


@user_passes_test(is_staff)
def manage_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'app/manage_orders.html', {'orders': orders})


@user_passes_test(is_staff)
def confirm_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Confirmed'
    order.save()
    return redirect('manage_orders')


@user_passes_test(is_staff)
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status != 'Delivered':
        order.status = 'Cancelled'
        order.save()
    return redirect('manage_orders')


def pack_and_ship(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        unit = request.POST.get('shipping_unit')
        order.status = 'Shipped'
        order.shipping_unit = unit
        order.save()
        OrderTracking.objects.create(
            order=order, status='Shipped',
            message=f'Đơn hàng đã được bàn giao cho đơn vị vận chuyển: {unit}.'
        )
    return redirect('manage_orders')


def staff_order_detail(request, order_id):
    if not request.user.is_staff:
        return redirect('home')
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'app/staff_order_detail.html', {'order': order, 'items': items})


# ── QUẢN LÝ SÁCH (STAFF) ─────────────────────────────────────────────────────
def staff_book_list(request):
    books = Book.objects.all()
    return render(request, 'app/staff_book_list.html', {'books': books})


def staff_book_insert(request):
    if request.method == "POST":
        category_id = request.POST.get('category')
        Book.objects.create(
            title=request.POST.get('title'),
            author=request.POST.get('author'),
            price=request.POST.get('price'),
            stock=request.POST.get('stock', 0),
            category=Category.objects.get(id=category_id) if category_id else None,
            release_date=request.POST.get('release_date') or timezone.now().date(),
            description=request.POST.get('description'),
            image=request.FILES.get('image'),
        )
        if "_addanother" in request.POST:
            return redirect('staff_book_insert')
        return redirect('staff_book_list')

    return render(request, 'app/staff_book_form.html', {'categories': Category.objects.all()})


def staff_book_update(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == "POST":
        book.title = request.POST.get('title')
        book.author = request.POST.get('author')
        book.price = request.POST.get('price')
        book.stock = request.POST.get('stock')
        category_id = request.POST.get('category')
        book.category = Category.objects.get(id=category_id) if category_id else None
        book.save()
        return redirect('staff_book_list')

    return render(request, 'app/staff_book_form.html', {
        'book': book, 'categories': Category.objects.all()
    })


def staff_book_delete(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        book.delete()
    return redirect('staff_book_list')


# ── CHAT ─────────────────────────────────────────────────────────────────────
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


# ── FLASH SALE (STAFF) ────────────────────────────────────────────────────────
@user_passes_test(is_staff)
def staff_flash_sale(request):
    config = FlashSaleConfig.get_config()

    if request.method == 'POST':
        config.is_active       = 'is_active' in request.POST
        config.discount_percent = int(request.POST.get('discount_percent', 30))
        config.start_hour      = int(request.POST.get('start_hour', 20))
        config.start_minute    = int(request.POST.get('start_minute', 0))
        config.end_hour        = int(request.POST.get('end_hour', 22))
        config.end_minute      = int(request.POST.get('end_minute', 0))

        # Validate đơn giản
        if not (0 <= config.discount_percent <= 99):
            messages.error(request, '% giảm giá phải từ 1 đến 99.')
        elif (config.start_hour * 60 + config.start_minute
              >= config.end_hour * 60 + config.end_minute):
            messages.error(request, 'Giờ bắt đầu phải trước giờ kết thúc.')
        else:
            config.save()
            messages.success(request, 'Đã lưu cấu hình flash sale!')
            return redirect('staff_flash_sale')

    return render(request, 'app/staff_flash_sale.html', {
        'config': config,
        'flash_active': config.is_sale_now(),
    })


@user_passes_test(is_staff)
def staff_flash_sale_toggle(request):
    """Bật/tắt nhanh flash sale không cần vào form."""
    if request.method == 'POST':
        config = FlashSaleConfig.get_config()
        config.is_active = not config.is_active
        config.save()
        state = 'BẬT' if config.is_active else 'TẮT'
        messages.success(request, f'Flash sale đã được {state}.')
    return redirect('staff_flash_sale')