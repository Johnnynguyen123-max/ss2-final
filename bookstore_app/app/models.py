# models.py
from django.db import models
from django.contrib.auth.models import User
from PIL import Image # Cần cài đặt Pillow: pip install Pillow
from django.utils import timezone  # THÊM DÒNG NÀY
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='default.jpg', upload_to='profile_pics')
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f'Hồ sơ của {self.user.username}'

    # Hàm resize ảnh để tránh làm nặng server
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.avatar.path)
        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.avatar.path)
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    
    # Thêm trường ngày ra mắt
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
    # Sửa on_relative thành on_delete
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"