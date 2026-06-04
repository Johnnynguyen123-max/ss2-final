import re
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ..models import Book, Order, OrderItem, Coupon


# ── THÊM VÀO GIỎ HÀNG ────────────────────────────────────────────────────────
def add_to_cart(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)

        # Kiểm tra tồn kho
        if book.stock <= 0:
            return JsonResponse({'status': 'error', 'message': 'Sách này đã hết hàng!'}, status=400)

        cart = request.session.get('cart', {})
        quantity = int(request.POST.get('quantity', 1))
        str_id = str(book_id)
        current_in_cart = cart.get(str_id, 0)
        new_quantity = current_in_cart + quantity

        # Không cho đặt vượt quá tồn kho
        if new_quantity > book.stock:
            available = book.stock - current_in_cart
            if available <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Bạn đã có {current_in_cart} quyển trong giỏ. Sách chỉ còn {book.stock} quyển trong kho!'
                }, status=400)
            new_quantity = book.stock
            cart[str_id] = new_quantity
            request.session['cart'] = cart
            request.session.modified = True
            return JsonResponse({
                'status': 'warning',
                'message': f'Chỉ còn {book.stock} quyển trong kho. Đã thêm tối đa {available} quyển vào giỏ hàng!',
                'total_items': sum(cart.values())
            })

        cart[str_id] = new_quantity
        request.session['cart'] = cart
        request.session.modified = True
        return JsonResponse({'status': 'success', 'total_items': sum(cart.values())})
    return JsonResponse({'status': 'error'}, status=400)


# ── XEM GIỎ HÀNG ─────────────────────────────────────────────────────────────
def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for book_id, quantity in cart.items():
        book = get_object_or_404(Book, id=book_id)
        # Tự động clamp nếu tồn kho giảm sau khi thêm vào giỏ
        if quantity > book.stock:
            quantity = book.stock
            cart[book_id] = quantity
            request.session['cart'] = cart
            request.session.modified = True
        if quantity > 0:
            subtotal = book.price * quantity
            total_price += subtotal
            cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})
    return render(request, 'app/cart.html', {'cart_items': cart_items, 'total_price': total_price})


# ── CẬP NHẬT GIỎ HÀNG ────────────────────────────────────────────────────────
def update_cart(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        cart = request.session.get('cart', {})
        action = request.POST.get('action')
        str_id = str(book_id)
        if str_id in cart:
            if action == 'increase':
                if cart[str_id] < book.stock:
                    cart[str_id] += 1
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Chỉ còn {book.stock} quyển trong kho!'
                    }, status=400)
            elif action == 'decrease':
                cart[str_id] = max(1, cart[str_id] - 1)
            request.session['cart'] = cart
            request.session.modified = True
            
            # Calculate updated numbers dynamically
            item_qty = cart[str_id]
            item_subtotal = int(book.price * item_qty)
            
            # Total price of the entire cart
            total_price = 0
            for b_id, q in cart.items():
                try:
                    b_obj = Book.objects.get(id=b_id)
                    total_price += b_obj.price * q
                except Book.DoesNotExist:
                    pass
                    
            total_items = sum(cart.values())
            
            return JsonResponse({
                'status': 'success',
                'quantity': item_qty,
                'subtotal': int(item_subtotal),
                'total_price': int(total_price),
                'total_items': total_items,
            })
    return JsonResponse({'status': 'error'}, status=400)


# ── XÓA KHỎI GIỎ HÀNG ────────────────────────────────────────────────────────
def remove_from_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        str_id = str(book_id)
        if str_id in cart:
            del cart[str_id]
            request.session['cart'] = cart
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


# ── VALIDATE COUPON (AJAX) ────────────────────────────────────────────────────
@login_required
def validate_coupon(request):
    """
    Nhận POST JSON { code, total } → trả về { valid, discount_percent, new_total, message }.
    """
    if request.method != 'POST':
        return JsonResponse({'valid': False, 'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Dữ liệu không hợp lệ'}, status=400)

    code = data.get('code', '').strip().upper()
    total = int(data.get('total', 0))

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return JsonResponse({'valid': False, 'message': 'Mã coupon không tồn tại.'})

    if not coupon.is_valid:
        if not coupon.is_active:
            msg = 'Mã coupon đã bị vô hiệu hóa.'
        elif coupon.valid_until < timezone.now().date():
            msg = f'Mã coupon đã hết hạn ngày {coupon.valid_until.strftime("%d/%m/%Y")}.'
        else:
            msg = 'Mã coupon đã đạt giới hạn sử dụng.'
        return JsonResponse({'valid': False, 'message': msg})

    discount_amount = int(total * coupon.discount_percent / 100)
    new_total = total - discount_amount
    return JsonResponse({
        'valid': True,
        'code': coupon.code,
        'discount_percent': coupon.discount_percent,
        'discount_amount': discount_amount,
        'new_total': new_total,
        'message': f'Áp dụng thành công! Giảm {coupon.discount_percent}% ({discount_amount:,}đ)',
    })


# ── CHECKOUT ──────────────────────────────────────────────────────────────────
def checkout(request):
    """
    Xử lý thanh toán đơn hàng.
    - GET : Hiển thị form thông tin giao hàng (hỗ trợ coupon via AJAX).
    - POST: Validate → giảm kho (atomic) → tạo Order + OrderItem → xóa giỏ hàng.
    """
    cart_session = request.session.get('cart', {})
    if not cart_session:
        messages.warning(request, "Giỏ hàng của bạn đang trống!")
        return redirect('cart_detail')

    cart_items = []
    total_bill = 0
    stock_errors = []
    for book_id, quantity in cart_session.items():
        book = get_object_or_404(Book, id=book_id)
        if quantity > book.stock:
            stock_errors.append(f'"{book.title}" chỉ còn {book.stock} quyển trong kho.')
            quantity = book.stock
            cart_session[book_id] = quantity
            request.session['cart'] = cart_session
            request.session.modified = True
        if quantity > 0:
            subtotal = book.price * quantity
            total_bill += subtotal
            cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})

    if stock_errors:
        for err in stock_errors:
            messages.warning(request, err)

    if request.user.is_authenticated:
        user_profile = getattr(request.user, 'profile', None)
        initial_full_name = f"{request.user.last_name} {request.user.first_name}".strip() or request.user.username
        initial_phone   = user_profile.phone    if user_profile else ""
        initial_address = user_profile.address  if user_profile else ""
    else:
        user_profile = None
        initial_full_name = ""
        initial_phone   = ""
        initial_address = ""

    # Lấy các mã giảm giá còn hạn và chưa dùng hết lượt (chỉ khả dụng với thành viên)
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_until__gt=timezone.now().date()
    ).filter(used_count__lt=F('max_uses')) if request.user.is_authenticated else Coupon.objects.none()

    if request.method == 'POST':
        full_name    = request.POST.get('full_name')
        phone        = request.POST.get('phone')
        address      = request.POST.get('address')
        coupon_code  = request.POST.get('coupon_code', '').strip().upper() if request.user.is_authenticated else ""
        final_total  = int(request.POST.get('final_total', total_bill))

        def re_render(extra=None):
            ctx = {
                'items': cart_items, 'total_bill': total_bill,
                'full_name': full_name, 'phone': phone, 'address': address,
                'coupon_code': coupon_code,
                'available_coupons': available_coupons,
            }
            if extra:
                ctx.update(extra)
            return render(request, 'app/checkout.html', ctx)

        if not all([full_name, phone, address]):
            messages.error(request, "Vui lòng điền đầy đủ thông tin giao hàng!")
            return re_render()

        if not re.match(r"^(0[35789])[0-9]{8}$", phone):
            messages.error(request, "Số điện thoại không đúng định dạng Việt Nam!")
            return re_render()

        # Xử lý coupon (chỉ cho thành viên)
        applied_coupon  = None
        discount_amount = 0
        if request.user.is_authenticated and coupon_code:
            try:
                coupon_obj = Coupon.objects.get(code=coupon_code)
                if coupon_obj.is_valid:
                    applied_coupon  = coupon_obj
                    discount_amount = int(total_bill * coupon_obj.discount_percent / 100)
                    final_total     = total_bill - discount_amount
            except Coupon.DoesNotExist:
                pass

        # Kiểm tra tồn kho khi submit
        for item in cart_items:
            if item['quantity'] > item['book'].stock:
                messages.error(request, f'"{item["book"].title}" chỉ còn {item["book"].stock} quyển. Vui lòng cập nhật giỏ hàng.')
                return redirect('cart_detail')

        try:
            with transaction.atomic():
                for item in cart_items:
                    updated = Book.objects.filter(
                        id=item['book'].id, stock__gte=item['quantity']
                    ).update(
                        stock=F('stock') - item['quantity'],
                        sold_count=F('sold_count') + item['quantity']
                    )
                    if not updated:
                        raise ValueError(f'"{item["book"].title}" vừa hết hàng. Vui lòng kiểm tra lại giỏ hàng.')

                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=full_name,
                    phone=phone,
                    address=address,
                    total_price=final_total,
                    coupon=applied_coupon,
                    discount_amount=discount_amount,
                )
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order, book=item['book'],
                        quantity=item['quantity'], price=item['book'].price
                    )

                # Tăng used_count của coupon
                if applied_coupon:
                    Coupon.objects.filter(pk=applied_coupon.pk).update(
                        used_count=F('used_count') + 1
                    )

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('cart_detail')

        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, f"Chúc mừng {full_name}, đơn hàng đã được hệ thống tiếp nhận!")
        return redirect('order_success', order_id=order.id)

    return render(request, 'app/checkout.html', {
        'items': cart_items, 'total_bill': total_bill,
        'full_name': initial_full_name, 'phone': initial_phone, 'address': initial_address,
        'available_coupons': available_coupons,
    })
