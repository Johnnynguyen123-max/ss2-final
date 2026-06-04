import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q

from ..models import Book, Category, Order, OrderItem, OrderTracking, FlashSaleConfig, Coupon


# ── HELPER: Kiểm tra quyền Staff ─────────────────────────────────────────────
def is_staff(user):
    return user.groups.filter(name='Staff').exists() or user.is_superuser


# ── DASHBOARD THỐNG KÊ (STAFF) ────────────────────────────────────────────────
@user_passes_test(is_staff)
def staff_dashboard(request):
    """
    Trang tổng quan cho staff: doanh thu 7 ngày, top sách bán chạy,
    phân bổ trạng thái đơn hàng, số liệu nhanh.
    """
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    # ── Số liệu nhanh (summary cards) ──
    total_orders    = Order.objects.count()
    pending_orders  = Order.objects.filter(status='Pending').count()
    revenue_today   = Order.objects.filter(
        created_at__date=today
    ).exclude(status='Cancelled').aggregate(s=Sum('total_price'))['s'] or 0
    total_books     = Book.objects.count()
    low_stock_books = Book.objects.filter(stock__lt=5).count()

    # ── Doanh thu 7 ngày gần nhất ──
    revenue_by_day = []
    labels_revenue = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        rev = Order.objects.filter(
            created_at__date=day
        ).exclude(status='Cancelled').aggregate(s=Sum('total_price'))['s'] or 0
        revenue_by_day.append(int(rev))
        labels_revenue.append(day.strftime('%d/%m'))

    # ── Top 5 sách bán chạy ──
    top_books = (
        OrderItem.objects
        .values('book__title')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )
    labels_books   = [b['book__title'][:20] for b in top_books]
    data_books     = [b['total_sold'] for b in top_books]

    # ── Phân bổ đơn hàng theo trạng thái ──
    status_counts = Order.objects.values('status').annotate(c=Count('id'))
    status_map    = {s['status']: s['c'] for s in status_counts}
    STATUS_LABELS = ['Pending', 'Confirmed', 'Shipped', 'Received', 'Cancelled']
    STATUS_VI     = ['Chờ xử lý', 'Đã xác nhận', 'Đang giao', 'Đã nhận', 'Đã hủy']
    data_status   = [status_map.get(k, 0) for k in STATUS_LABELS]

    # ── Đơn hàng mới nhất (10 đơn) ──
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    return render(request, 'app/staff_dashboard.html', {
        # Summary
        'total_orders':    total_orders,
        'pending_orders':  pending_orders,
        'revenue_today':   revenue_today,
        'total_books':     total_books,
        'low_stock_books': low_stock_books,
        # Chart data (JSON strings for inline JS)
        'labels_revenue':  json.dumps(labels_revenue),
        'data_revenue':    json.dumps(revenue_by_day),
        'labels_books':    json.dumps(labels_books),
        'data_books':      json.dumps(data_books),
        'labels_status':   json.dumps(STATUS_VI),
        'data_status':     json.dumps(data_status),
        # Table
        'recent_orders':   recent_orders,
    })


# ── QUẢN LÝ ĐƠN HÀNG (STAFF) ─────────────────────────────────────────────────
@user_passes_test(is_staff)
def manage_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'app/manage_orders.html', {'orders': orders})


@user_passes_test(is_staff)
@require_POST
def confirm_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Pending':
        order.status = 'Confirmed'
        order.save(update_fields=['status'])
    return redirect('manage_orders')


@user_passes_test(is_staff)
@require_POST
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status != 'Delivered':
        order.status = 'Cancelled'
        order.save()
    return redirect('manage_orders')


@user_passes_test(is_staff)
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


@user_passes_test(is_staff)
def staff_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'app/staff_order_detail.html', {'order': order, 'items': items})


@user_passes_test(is_staff)
@require_POST
def staff_confirm_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'Shipped':
        order.status = 'Received'
        order.save(update_fields=['status'])
        OrderTracking.objects.create(
            order=order, status='Received',
            message='Giao hàng thành công. Nhân viên cửa hàng đã xác nhận hoàn tất giao hàng.'
        )
        messages.success(request, f"Đơn hàng #{order.id} đã hoàn tất thành công.")
    return redirect('manage_orders')



# ── QUẢN LÝ SÁCH (STAFF) ─────────────────────────────────────────────────────
@user_passes_test(is_staff)
def staff_book_list(request):
    books = Book.objects.select_related('category')
    return render(request, 'app/staff_book_list.html', {'books': books})


@user_passes_test(is_staff)
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


@user_passes_test(is_staff)
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


@user_passes_test(is_staff)
def staff_book_delete(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        book.delete()
    return redirect('staff_book_list')


# ── FLASH SALE (STAFF) ────────────────────────────────────────────────────────
@user_passes_test(is_staff)
def staff_flash_sale(request):
    config = FlashSaleConfig.get_config()
    if request.method == 'POST':
        config.is_active        = 'is_active' in request.POST
        config.discount_percent = int(request.POST.get('discount_percent', 10))
        config.start_hour       = int(request.POST.get('start_hour', 20))
        config.start_minute     = int(request.POST.get('start_minute', 0))
        config.end_hour         = int(request.POST.get('end_hour', 22))
        config.end_minute       = int(request.POST.get('end_minute', 0))
        config.save()
        messages.success(request, 'Đã lưu cấu hình Flash Sale!')
        return redirect('staff_flash_sale')
    return render(request, 'app/staff_flash_sale.html', {
        'config': config,
        'flash_active': config.is_running_now,
    })


@user_passes_test(is_staff)
@require_POST
def staff_flash_sale_toggle(request):
    config = FlashSaleConfig.get_config()
    config.is_active = not config.is_active
    config.save(update_fields=['is_active'])
    status = 'bật' if config.is_active else 'tắt'
    messages.success(request, f'Flash Sale đã {status}.')
    return redirect('staff_flash_sale')


@user_passes_test(is_staff)
def staff_coupon_list(request):
    coupons = Coupon.objects.all().order_by('-valid_until')
    return render(request, 'app/staff_coupon_list.html', {'coupons': coupons})


@user_passes_test(is_staff)
def staff_coupon_create(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        discount_percent = int(request.POST.get('discount_percent', 10))
        valid_until = request.POST.get('valid_until')
        max_uses = int(request.POST.get('max_uses', 100))
        is_active = True

        if not code or not valid_until:
            messages.error(request, "Vui lòng nhập đầy đủ mã coupon và ngày hết hạn.")
            return render(request, 'app/staff_coupon_form.html')

        if Coupon.objects.filter(code=code).exists():
            messages.error(request, f"Mã coupon '{code}' đã tồn tại.")
            return render(request, 'app/staff_coupon_form.html')

        try:
            Coupon.objects.create(
                code=code,
                discount_percent=discount_percent,
                valid_until=valid_until,
                max_uses=max_uses,
                is_active=is_active
            )
            messages.success(request, f"Đã thêm mới coupon '{code}' thành công.")
            return redirect('staff_coupon_list')
        except Exception as e:
            messages.error(request, f"Lỗi tạo coupon: {str(e)}")
            return render(request, 'app/staff_coupon_form.html')

    return render(request, 'app/staff_coupon_form.html')


@user_passes_test(is_staff)
def staff_coupon_update(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        discount_percent = int(request.POST.get('discount_percent', 10))
        valid_until = request.POST.get('valid_until')
        max_uses = int(request.POST.get('max_uses', 100))
        is_active = True

        if not code or not valid_until:
            messages.error(request, "Vui lòng điền đầy đủ mã coupon và ngày hết hạn.")
            return render(request, 'app/staff_coupon_form.html', {'coupon': coupon})

        # Kiểm tra trùng mã (trừ chính nó)
        if Coupon.objects.filter(code=code).exclude(id=coupon.id).exists():
            messages.error(request, f"Mã coupon '{code}' đã được sử dụng bởi coupon khác.")
            return render(request, 'app/staff_coupon_form.html', {'coupon': coupon})

        try:
            coupon.code = code
            coupon.discount_percent = discount_percent
            coupon.valid_until = valid_until
            coupon.max_uses = max_uses
            coupon.is_active = is_active
            coupon.save()
            messages.success(request, f"Đã cập nhật coupon '{code}' thành công.")
            return redirect('staff_coupon_list')
        except Exception as e:
            messages.error(request, f"Lỗi cập nhật coupon: {str(e)}")
            return render(request, 'app/staff_coupon_form.html', {'coupon': coupon})

    # Đưa định dạng ngày về YYYY-MM-DD để đưa vào input date
    formatted_date = coupon.valid_until.strftime('%Y-%m-%d') if coupon.valid_until else ''
    return render(request, 'app/staff_coupon_form.html', {
        'coupon': coupon,
        'formatted_date': formatted_date
    })


@user_passes_test(is_staff)
@require_POST
def staff_coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    code = coupon.code
    coupon.delete()
    messages.success(request, f"Đã xóa coupon '{code}' thành công.")
    return redirect('staff_coupon_list')
