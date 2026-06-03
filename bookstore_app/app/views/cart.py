import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F

from ..models import Book, Order, OrderItem


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
            # Chỉ thêm đúng số lượng còn có thể thêm
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
            return JsonResponse({'status': 'success'})
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


# ── CHECKOUT ──────────────────────────────────────────────────────────────────
@login_required
def checkout(request):
    cart_session = request.session.get('cart', {})
    if not cart_session:
        messages.warning(request, "Giỏ hàng của bạn đang trống!")
        return redirect('cart_detail')

    cart_items = []
    total_bill = 0
    stock_errors = []
    for book_id, quantity in cart_session.items():
        book = get_object_or_404(Book, id=book_id)
        # Kiểm tra tồn kho lần cuối trước khi thanh toán
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

        # Kiểm tra tồn kho một lần nữa khi submit
        for item in cart_items:
            if item['quantity'] > item['book'].stock:
                messages.error(request, f'"{item["book"].title}" chỉ còn {item["book"].stock} quyển. Vui lòng cập nhật giỏ hàng.')
                return redirect('cart_detail')

        try:
            with transaction.atomic():
                # Kiểm tra và giảm kho atomic – tránh race condition đồng thời
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
                    user=request.user, full_name=full_name,
                    phone=phone, address=address, total_price=total_bill
                )
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order, book=item['book'],
                        quantity=item['quantity'], price=item['book'].price
                    )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('cart_detail')

        request.session['cart'] = {}
        request.session.modified = True
        messages.success(request, f"Chúc mừng {full_name}, đơn hàng đã được hệ thống tiếp nhận!")
        return render(request, 'app/checkout.html', {'items': [], 'total_bill': 0})

    return render(request, 'app/checkout.html', {
        'items': cart_items, 'total_bill': total_bill,
        'full_name': initial_full_name, 'phone': initial_phone, 'address': initial_address
    })
