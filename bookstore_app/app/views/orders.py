from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from ..models import Order, OrderItem, OrderTracking


# ── LỊCH SỬ ĐƠN HÀNG ────────────────────────────────────────────────────────
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)\
        .prefetch_related('items__book')\
        .order_by('-created_at')
    return render(request, 'app/order_history.html', {'orders': orders})


# ── HỦY ĐƠN HÀNG ─────────────────────────────────────────────────────────────
@login_required
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Chỉ cho hủy khi đang Pending — các trạng thái khác đã khóa nút rồi
    if order.status != 'Pending':
        messages.error(request, "Không thể hủy đơn hàng này.")
        return redirect('order_history')

    # Hoàn tồn kho cho từng sản phẩm
    for item in order.items.all():
        item.book.stock += item.quantity
        item.book.sold_count = max(0, item.book.sold_count - item.quantity)
        item.book.save(update_fields=['stock', 'sold_count'])

    order.status = 'Cancelled'
    order.save(update_fields=['status'])
    messages.success(request, "Đã hủy đơn hàng thành công.")
    return redirect('order_history')


# ── CẬP NHẬT THÔNG TIN ĐƠN HÀNG ─────────────────────────────────────────────
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


# ── THEO DÕI ĐƠN HÀNG ────────────────────────────────────────────────────────
@login_required
def order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'app/order_tracking.html', {
        'order': order,
        'order_items': order.items.all(),
    })


# ── XÁC NHẬN ĐÃ NHẬN HÀNG ───────────────────────────────────────────────────
@login_required
@require_POST
def confirm_received(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Shipped':
        order.status = 'Received'           # ← khớp với template
        order.save(update_fields=['status'])
        OrderTracking.objects.create(
            order=order, status='Received',  # ← khớp
            message='Giao hàng thành công. Người mua đã xác nhận nhận hàng.'
        )
    return redirect('order_history')
