# app/context_processors.py
from .models import Category

def categories_processor(request):
    # Lấy toàn bộ danh mục để dùng chung cho mọi template
    return {
        'categories': Category.objects.all()
    }