# models.py
from django.db import models
from django.contrib.auth.models import User
from PIL import Image # Cần cài đặt Pillow: pip install Pillow
from django.utils import timezone  # THÊM DÒNG NÀY
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
        # Tối ưu ảnh sau khi save
        if self.avatar and os.path.exists(self.avatar.path):
            img = Image.open(self.avatar.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
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
    
    # Bổ sung trường số lượng tồn kho
    stock = models.IntegerField(default=0) 
    
    # Giữ nguyên các trường cũ
    release_date = models.DateField(default=timezone.now) 
    wishlist = models.ManyToManyField(User, related_name="favorite_books", blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='books/', blank=True, null=True)

    def __str__(self):
        return self.title

    # Hàm kiểm tra sách mới (Logic 3 tháng)
    @property
    def is_new(self):
        three_months_ago = timezone.now().date() - timedelta(days=90)
        return self.release_date >= three_months_ago
class Comment(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    rating = models.IntegerField(default=5) # Thêm dòng này để lưu số sao
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.book.title}'
class Order(models.Model):
    # Trạng thái đơn hàng
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
    price = models.DecimalField(max_digits=12, decimal_places=0) # Lưu giá tại thời điểm mua
    @property
    def get_total_item(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity} x {self.book.title}"
# Thêm vào app/models.py (Nếu Đăng muốn dùng Tracking)
class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trackings')
    status = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.id} - {self.status}"
class ChatSession(models.Model):
    """Một phòng chat giữa 1 customer và staff"""
    customer = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='chat_session'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-last_message_at']
 
    def __str__(self):
        return f"Chat – {self.customer.get_full_name() or self.customer.username}"
 
    def unread_for_staff(self):
        """Số tin chưa đọc của customer gửi lên (staff chưa đọc)"""
        return self.messages.filter(sender=self.customer, is_read=False).count()
 
    def last_message(self):
        return self.messages.order_by('-created_at').first()
 
 
class ChatMessage(models.Model):
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_chat_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['created_at']
    
    
