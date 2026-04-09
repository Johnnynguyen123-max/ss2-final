from django.contrib import admin

from .models import Book, Comment,Category

admin.site.register(Book)
admin.site.register(Comment)
admin.site.register(Category)
