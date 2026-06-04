# models.py
from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.utils import timezone
from datetime import timedelta
import os


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(default='default.jpg', upload_to='profile_pics')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Hồ sơ của {self.user.username}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.avatar and os.path.exists(self.avatar.path):
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                img.thumbnail((300, 300))
                img.save(self.avatar.path)


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='books')
    stock = models.IntegerField(default=0)
    release_date = models.DateField(default=timezone.now)
    wishlist = models.ManyToManyField(User, related_name="favorite_books", blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='books/', blank=True, null=True)
    sold_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def is_new(self):
        three_months_ago = timezone.now().date() - timedelta(days=90)
        return self.release_date >= three_months_ago


class Comment(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    rating = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'


class Coupon(models.Model):
    """Mã giảm giá áp dụng khi thanh toán."""
    code             = models.CharField(max_length=20, unique=True, verbose_name='Mã coupon')
    discount_percent = models.IntegerField(default=10, verbose_name='Giảm (%)')
    valid_until      = models.DateField(verbose_name='Hết hạn')
    max_uses         = models.IntegerField(default=100, verbose_name='Số lần dùng tối đa')
    used_count       = models.IntegerField(default=0, verbose_name='Đã dùng')
    is_active        = models.BooleanField(default=True, verbose_name='Đang hoạt động')

    class Meta:
        verbose_name = 'Mã giảm giá'
        verbose_name_plural = 'Mã giảm giá'

    def __str__(self):
        return f'{self.code} – {self.discount_percent}%'

    @property
    def is_valid(self):
        """Kiểm tra coupon còn hiệu lực không."""
        from django.utils import timezone
        return (
            self.is_active
            and self.valid_until > timezone.now().date()
            and self.used_count < self.max_uses
        )


class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending',    'Chờ xử lý'),
        ('Confirmed',  'Đã xác nhận'),
        ('Shipped',    'Đang giao'),
        ('Received',   'Đã nhận hàng'),
        ('Cancelled',  'Đã hủy'),
    )

    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name       = models.CharField(max_length=255)
    phone           = models.CharField(max_length=20)
    address         = models.TextField()
    total_price     = models.DecimalField(max_digits=12, decimal_places=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    shipping_unit   = models.CharField(max_length=50, blank=True, null=True)
    coupon          = models.ForeignKey('Coupon', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='orders', verbose_name='Mã giảm giá')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                          verbose_name='Số tiền giảm')

    def mark_as_shipped(self, unit_name):
        self.status = 'Shipped'
        self.shipping_unit = unit_name
        self.save()

    def __str__(self):
        return f"Đơn hàng {self.id} - {self.full_name}"




class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=0)

    @property
    def get_total_item(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity} x {self.book.title}"


class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trackings')
    status = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} - {self.status}"


class ChatSession(models.Model):
    customer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_session')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at']

    def __str__(self):
        return f"Chat – {self.customer.get_full_name() or self.customer.username}"

    def unread_for_staff(self):
        return self.messages.filter(sender=self.customer, is_read=False).count()

    def last_message(self):
        return self.messages.order_by('-created_at').first()


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class FlashSaleConfig(models.Model):
    """Cấu hình Flash Sale – chỉ có 1 bản ghi duy nhất (singleton)."""
    is_active       = models.BooleanField(default=False)
    discount_percent = models.IntegerField(default=10)
    start_hour      = models.IntegerField(default=20)
    start_minute    = models.IntegerField(default=0)
    end_hour        = models.IntegerField(default=22)
    end_minute      = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Cấu hình Flash Sale'

    def __str__(self):
        return f'Flash Sale – {self.discount_percent}% ({self.start_hour:02d}:{self.start_minute:02d}–{self.end_hour:02d}:{self.end_minute:02d})'

    @classmethod
    def get_config(cls):
        """Trả về config duy nhất, tạo mới nếu chưa có."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_running_now(self):
        """Kiểm tra flash sale có đang chạy tại thời điểm này không."""
        if not self.is_active:
            return False
        now = timezone.now().astimezone()
        now_minutes = now.hour * 60 + now.minute
        start_minutes = self.start_hour * 60 + self.start_minute
        end_minutes   = self.end_hour   * 60 + self.end_minute
        if start_minutes < end_minutes:
            return start_minutes <= now_minutes < end_minutes
        return now_minutes >= start_minutes or now_minutes < end_minutes


class BotChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='bot_sessions')
    session_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_message_at']

    def __str__(self):
        if self.user:
            return f"BotSession – {self.user.username}"
        return f"BotSession Guest – {self.session_key[:8] if self.session_key else 'Unknown'}"


class BotChatMessage(models.Model):
    session = models.ForeignKey(BotChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'AI Bot')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=0)  # 0: neutral, 1: thumbs up, -1: thumbs down

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:30]}"


class PriceAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='price_alerts')
    session_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='price_alerts')
    target_price = models.DecimalField(max_digits=10, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Alert for {self.book.title} @ {self.target_price}"