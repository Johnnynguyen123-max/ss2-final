from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Case, When
from django.views.decorators.http import require_POST

from ..models import Book, Comment


# ── CHI TIẾT SÁCH ─────────────────────────────────────────────────────────────
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    related_books = Book.objects.filter(category=book.category).exclude(id=book_id).select_related('category')[:5]

    if 'recently_viewed' not in request.session:
        request.session['recently_viewed'] = []
    recently_viewed = request.session['recently_viewed']
    if book_id in recently_viewed:
        recently_viewed.remove(book_id)
    recently_viewed.insert(0, book_id)
    request.session['recently_viewed'] = recently_viewed[:6]
    request.session.modified = True

    comments = book.comments.all().order_by('-created_at')
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = book.wishlist.filter(id=request.user.id).exists()

    return render(request, 'app/book_detail.html', {
        'book': book,
        'comments': comments,
        'is_favorite': is_favorite,
        'related_books': related_books,
    })


# ── BÌNH LUẬN ────────────────────────────────────────────────────────────────
@login_required
def post_comment(request, book_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        rating = request.POST.get('rating', 5)
        if content:
            book = get_object_or_404(Book, id=book_id)
            Comment.objects.create(book=book, user=request.user, content=content, rating=int(rating))
    return redirect('book_detail', book_id=book_id)


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    book_id = comment.book.id
    if request.user == comment.user or request.user.is_superuser:
        comment.delete()
        messages.success(request, "Đã xóa bình luận thành công.")
    else:
        messages.error(request, "Bạn không có quyền xóa bình luận này.")
    return redirect('book_detail', book_id=book_id)
