"""
admin.py — Tùy chỉnh Django Admin cho toàn bộ models của ứng dụng.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Profile, Category, Book, Comment,
    Order, OrderItem, OrderTracking,
    ChatSession, ChatMessage,
    FlashSaleConfig, Coupon,
)

# ══════════════════════════════════════════════════════
#  Admin site branding
# ══════════════════════════════════════════════════════
admin.site.site_header  = "DDC Books – Quản trị"
admin.site.site_title   = "DDC Books Admin"
admin.site.index_title  = "Bảng điều khiển"


# ══════════════════════════════════════════════════════
#  Profile
# ══════════════════════════════════════════════════════
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'phone', 'address')
    search_fields = ('user__username', 'user__email', 'phone')
    raw_id_fields = ('user',)


# ══════════════════════════════════════════════════════
#  Category
# ══════════════════════════════════════════════════════
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name')
    search_fields = ('name',)


# ══════════════════════════════════════════════════════
#  Book
# ══════════════════════════════════════════════════════
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display   = ('thumbnail', 'title', 'author', 'category',
                      'price_display', 'stock', 'sold_count', 'release_date', 'is_new_badge')
    list_filter    = ('category', 'release_date')
    search_fields  = ('title', 'author')
    list_per_page  = 25
    ordering       = ('-release_date',)
    readonly_fields = ('sold_count', 'thumbnail')
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('title', 'author', 'category', 'description', 'image', 'thumbnail')
        }),
        ('Giá & Kho', {
            'fields': ('price', 'stock', 'sold_count', 'release_date')
        }),
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px;border-radius:4px;">', obj.image.url)
        return '—'
    thumbnail.short_description = 'Ảnh'

    def price_display(self, obj):
        return f'{int(obj.price):,}đ'
    price_display.short_description = 'Giá'
    price_display.admin_order_field = 'price'

    def is_new_badge(self, obj):
        if obj.is_new:
            return format_html('<span style="color:green;font-weight:bold;">✔ Mới</span>')
        return '—'
    is_new_badge.short_description = 'Sách mới?'


# ══════════════════════════════════════════════════════
#  Comment
# ══════════════════════════════════════════════════════
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('user', 'book', 'rating', 'short_content', 'created_at')
    list_filter   = ('rating',)
    search_fields = ('user__username', 'book__title', 'content')
    ordering      = ('-created_at',)

    def short_content(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
    short_content.short_description = 'Nội dung'


# ══════════════════════════════════════════════════════
#  Order + OrderItem (inline)
# ══════════════════════════════════════════════════════
class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    fields = ('book', 'quantity', 'price', 'item_total')
    readonly_fields = ('item_total',)

    def item_total(self, obj):
        return f'{int(obj.quantity * obj.price):,}đ'
    item_total.short_description = 'Thành tiền'


class OrderTrackingInline(admin.TabularInline):
    model   = OrderTracking
    extra   = 0
    fields  = ('status', 'message', 'created_at')
    readonly_fields = ('created_at',)


STATUS_COLORS = {
    'Pending':   '#f39c12',
    'Confirmed': '#3498db',
    'Shipped':   '#8e44ad',
    'Received':  '#27ae60',
    'Cancelled': '#e74c3c',
}

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ('id', 'full_name', 'user', 'status_badge',
                      'total_price_display', 'discount_display', 'coupon', 'created_at')
    list_filter    = ('status', 'created_at')
    search_fields  = ('full_name', 'phone', 'user__username', 'user__email')
    ordering       = ('-created_at',)
    list_per_page  = 30
    inlines        = [OrderItemInline, OrderTrackingInline]
    readonly_fields = ('created_at', 'discount_amount')
    fieldsets = (
        ('Thông tin người đặt', {
            'fields': ('user', 'full_name', 'phone', 'address')
        }),
        ('Thanh toán', {
            'fields': ('total_price', 'coupon', 'discount_amount')
        }),
        ('Trạng thái & Vận chuyển', {
            'fields': ('status', 'shipping_unit', 'created_at')
        }),
    )

    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, '#999')
        label = dict(Order.STATUS_CHOICES).get(obj.status, obj.status)
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:0.8em;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Trạng thái'
    status_badge.admin_order_field = 'status'

    def total_price_display(self, obj):
        return f'{int(obj.total_price):,}đ'
    total_price_display.short_description = 'Tổng tiền'
    total_price_display.admin_order_field = 'total_price'

    def discount_display(self, obj):
        if obj.discount_amount:
            return format_html('<span style="color:#e74c3c;">-{:,}đ</span>', int(obj.discount_amount))
        return '—'
    discount_display.short_description = 'Giảm giá'


# ══════════════════════════════════════════════════════
#  Coupon
# ══════════════════════════════════════════════════════
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ('code', 'discount_percent', 'valid_until',
                     'used_count', 'max_uses', 'is_active', 'validity_badge')
    list_filter   = ('is_active',)
    search_fields = ('code',)
    ordering      = ('-valid_until',)
    readonly_fields = ('used_count',)

    def validity_badge(self, obj):
        if obj.is_valid:
            return format_html('<span style="color:green;font-weight:bold;">✔ Còn hiệu lực</span>')
        return format_html('<span style="color:#e74c3c;font-weight:bold;">✘ Hết hiệu lực</span>')
    validity_badge.short_description = 'Trạng thái'


# ══════════════════════════════════════════════════════
#  Flash Sale Config
# ══════════════════════════════════════════════════════
@admin.register(FlashSaleConfig)
class FlashSaleConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active', 'discount_percent',
                    'start_hour', 'start_minute', 'end_hour', 'end_minute')


# ══════════════════════════════════════════════════════
#  Chat
# ══════════════════════════════════════════════════════
class ChatMessageInline(admin.TabularInline):
    model  = ChatMessage
    extra  = 0
    fields = ('sender', 'content', 'is_read', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display  = ('customer', 'created_at', 'last_message_at', 'unread_count')
    search_fields = ('customer__username',)
    inlines       = [ChatMessageInline]

    def unread_count(self, obj):
        count = obj.unread_for_staff()
        if count:
            return format_html('<span style="color:#e74c3c;font-weight:bold;">{}</span>', count)
        return '0'
    unread_count.short_description = 'Tin chưa đọc'
