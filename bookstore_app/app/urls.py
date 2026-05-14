from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # ── Trang chủ & xác thực ──────────────────────────────────
    path('',                                views.home,                name='home'),
    path('login/',                          views.login_view,          name='login'),
    path('signup/',                         views.signup,              name='signup'),
    path('logout/',                         views.logout_view,         name='logout'),
    path('profile/',                        views.profile,             name='profile'),

    # ── Sách ──────────────────────────────────────────────────
    path('book/<int:book_id>/',             views.book_detail,         name='book_detail'),
    path('search-suggestions/',             views.search_suggestions,  name='search_suggestions'),
    path('post-comment/<int:book_id>/',     views.post_comment,        name='post_comment'),
    path('delete-comment/<int:comment_id>/',views.delete_comment,      name='delete_comment'),

    # ── Giỏ hàng ──────────────────────────────────────────────
    path('cart/',                           views.cart_detail,         name='cart_detail'),
    path('add-to-cart/<int:book_id>/',      views.add_to_cart,         name='add_to_cart'),
    path('update-cart/<int:book_id>/',      views.update_cart,         name='update_cart'),
    path('remove-from-cart/<int:book_id>/', views.remove_from_cart,    name='remove_from_cart'),
    path('checkout/',                       views.checkout,            name='checkout'),

    # ── Wishlist ──────────────────────────────────────────────
    path('toggle-wishlist/',                views.toggle_wishlist,     name='toggle_wishlist'),
    path('my-wishlist/',                    views.wishlist_list,       name='wishlist_list'),

    # ── Đơn hàng (khách hàng) ─────────────────────────────────
    path('order-history/',                  views.order_history,       name='order_history'),
    path('order/delete/<int:order_id>/',    views.delete_order,        name='delete_order'),
    path('order/update/<int:order_id>/',    views.update_order_info,   name='update_order_info'),
    path('order-tracking/<int:order_id>/',  views.order_tracking,      name='order_tracking'),
    path('order/received/<int:order_id>/',  views.confirm_received,    name='confirm_received'),

    # ── Quản lý đơn hàng (staff) ──────────────────────────────
    path('manage-orders/',                       views.manage_orders,      name='manage_orders'),
    path('confirm-order/<int:order_id>/',         views.confirm_order,      name='confirm_order'),
    path('cancel-order/<int:order_id>/',          views.cancel_order,       name='cancel_order'),
    path('order/pack-and-ship/<int:order_id>/',   views.pack_and_ship,      name='pack_and_ship'),
    path('staff/order/<int:order_id>/',           views.staff_order_detail, name='staff_order_detail'),

    # ── Quản lý sách (staff) ──────────────────────────────────
    path('staff/books/',                          views.staff_book_list,        name='staff_book_list'),
    path('staff/books/insert/',                   views.staff_book_insert,      name='staff_book_insert'),
    path('staff/books/update/<int:book_id>/',     views.staff_book_update,      name='staff_book_update'),
    path('staff/books/delete/<int:book_id>/',     views.staff_book_delete,      name='staff_book_delete'),

    # ── Flash Sale (staff) ────────────────────────────────────
    path('staff/flash-sale/',                     views.staff_flash_sale,        name='staff_flash_sale'),
    path('staff/flash-sale/toggle/',              views.staff_flash_sale_toggle, name='staff_flash_sale_toggle'),

    # ── Chat ──────────────────────────────────────────────────
    path('chat/customer/send/',                   views.customer_send,   name='customer_send'),
    path('chat/customer/poll/',                   views.customer_poll,   name='customer_poll'),
    path('chat/staff/sessions/',                  views.staff_sessions,  name='staff_sessions'),
    path('chat/staff/<int:session_id>/poll/',     views.staff_poll,      name='staff_poll'),
    path('chat/staff/<int:session_id>/send/',     views.staff_send,      name='staff_send'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)