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


# ── XÁC NHẬN ĐƠN HÀNG THÀNH CÔNG ──────────────────────────────────────────────
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'app/order_success.html', {
        'order': order,
        'order_items': order.items.all(),
    })


# ── TRA CỨU ĐƠN HÀNG GUEST ──────────────────────────────────────────────────
def track_order_guest(request):
    order = None
    searched = False
    error_msg = None
    
    order_id = (request.POST.get('order_id') or request.GET.get('order_id') or '').strip()
    phone = (request.POST.get('phone') or request.GET.get('phone') or '').strip()
    
    if order_id or phone:
        if order_id and phone:
            try:
                order = Order.objects.prefetch_related('items__book').get(id=order_id, phone=phone)
            except (Order.DoesNotExist, ValueError):
                error_msg = "Không tìm thấy đơn hàng phù hợp với mã đơn và số điện thoại đã cung cấp."
            searched = True
        else:
            error_msg = "Vui lòng cung cấp cả mã đơn hàng và số điện thoại để tra cứu."
            searched = True

    return render(request, 'app/track_order.html', {
        'order': order,
        'searched': searched,
        'error_msg': error_msg,
        'order_id': order_id,
        'phone': phone,
    })


# ── XÁC NHẬN ĐÃ NHẬN HÀNG GUEST ─────────────────────────────────────────────
@require_POST
def confirm_received_guest(request, order_id):
    phone = request.POST.get('phone', '').strip()
    order = get_object_or_404(Order, id=order_id, phone=phone)
    if order.status == 'Shipped':
        order.status = 'Received'
        order.save(update_fields=['status'])
        OrderTracking.objects.create(
            order=order, status='Received',
            message='Giao hàng thành công. Khách vãng lai đã xác nhận nhận hàng.'
        )
        messages.success(request, "Cảm ơn bạn đã xác nhận đã nhận hàng thành công!")
    return redirect(f'/track-order/?order_id={order.id}&phone={order.phone}')


