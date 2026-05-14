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


class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Chờ xử lý'),
        ('Processing', 'Đang đóng gói'),
        ('Shipped', 'Đang giao'),
        ('Delivered', 'Đã nhận hàng'),
        ('Cancelled', 'Đã hủy'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    total_price = models.DecimalField(max_digits=12, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    shipping_unit = models.CharField(max_length=50, blank=True, null=True)

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


# ── FLASH SALE ────────────────────────────────────────────────────────────────
class FlashSaleConfig(models.Model):
    """
    Cấu hình flash sale theo khung giờ lặp lại mỗi ngày.
    Chỉ nên có 1 bản ghi active tại một thời điểm.
    Staff vào /staff/flash-sale/ để chỉnh.
    """
    is_active = models.BooleanField(default=False, verbose_name='Bật flash sale')
    discount_percent = models.PositiveIntegerField(
        default=30,
        verbose_name='% giảm giá',
        help_text='Nhập số nguyên, VD: 30 → giảm 30%'
    )
    start_hour   = models.PositiveIntegerField(default=20, verbose_name='Giờ bắt đầu (0-23)')
    start_minute = models.PositiveIntegerField(default=0,  verbose_name='Phút bắt đầu (0-59)')
    end_hour     = models.PositiveIntegerField(default=22, verbose_name='Giờ kết thúc (0-23)')
    end_minute   = models.PositiveIntegerField(default=0,  verbose_name='Phút kết thúc (0-59)')
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cấu hình Flash Sale'

    def __str__(self):
        status = 'BẬT' if self.is_active else 'TẮT'
        return (f"Flash Sale [{status}] — -{self.discount_percent}% "
                f"({self.start_hour:02d}:{self.start_minute:02d}"
                f"–{self.end_hour:02d}:{self.end_minute:02d})")

    @classmethod
    def get_config(cls):
        """Trả về config hiện tại, tạo mới nếu chưa có."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_sale_now(self):
        """Kiểm tra hiện tại có đang trong khung giờ flash sale không."""
        if not self.is_active:
            return False
        now = timezone.localtime(timezone.now())
        current_minutes = now.hour * 60 + now.minute
        start_minutes   = self.start_hour * 60 + self.start_minute
        end_minutes     = self.end_hour   * 60 + self.end_minute
        return start_minutes <= current_minutes < end_minutes

    def discounted_price(self, original_price):
        """Tính giá sau giảm (trả về int để dễ hiển thị)."""
        return int(original_price * (100 - self.discount_percent) / 100)