# app/views/__init__.py
#
# File này tập hợp (re-export) tất cả các hàm view từ các module con.
# Nhờ đó, file urls.py vẫn dùng cú pháp "from . import views" như cũ
# mà không cần thay đổi bất kỳ dòng nào.

from .home import (
    home,
    search_suggestions,
)

from .auth import (
    signup,
    login_view,
    logout_view,
    profile,
)

from .books import (
    book_detail,
    post_comment,
    delete_comment,
)

from .wishlist import (
    toggle_wishlist,
    wishlist_list,
)

from .cart import (
    add_to_cart,
    cart_detail,
    update_cart,
    remove_from_cart,
    checkout,
)

from .orders import (
    order_history,
    delete_order,
    update_order_info,
    order_tracking,
    confirm_received,
)

from .staff import (
    is_staff,
    manage_orders,
    confirm_order,
    cancel_order,
    pack_and_ship,
    staff_order_detail,
    staff_book_list,
    staff_book_insert,
    staff_book_update,
    staff_book_delete,
    staff_flash_sale,
    staff_flash_sale_toggle,
)

from .chat import (
    customer_send,
    customer_poll,
    staff_sessions,
    staff_poll,
    staff_send,
    chat_bot,
)
