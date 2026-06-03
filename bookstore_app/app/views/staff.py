from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Book, Category, Order, OrderItem, OrderTracking, FlashSaleConfig


# ── HELPER: Kiểm tra quyền Staff ─────────────────────────────────────────────
# Định nghĩa is_staff TRƯỚC tất cả @user_passes_test(is_staff) để tránh NameError
def is_staff(user):
    return user.groups.filter(name='Staff').exists() or user.is_superuser


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
