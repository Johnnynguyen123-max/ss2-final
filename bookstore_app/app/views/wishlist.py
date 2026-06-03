import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from ..models import Book


# ── WISHLIST ──────────────────────────────────────────────────────────────────
@login_required
def toggle_wishlist(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            if not book_id:
                return JsonResponse({'status': 'error', 'message': 'Thiếu ID sách'}, status=400)

            from django.shortcuts import get_object_or_404
            book = get_object_or_404(Book, id=book_id)
            if book.wishlist.filter(id=request.user.id).exists():
                book.wishlist.remove(request.user)
                action, is_favorite = 'removed', False
            else:
                book.wishlist.add(request.user)
                action, is_favorite = 'added', True

            return JsonResponse({'status': 'success', 'action': action, 'is_favorite': is_favorite})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'}, status=405)


@login_required
def wishlist_list(request):
    favorite_books = Book.objects.filter(wishlist=request.user).order_by('-id')
    return render(request, 'app/wishlist.html', {
        'books': favorite_books,
        'title': 'Sách yêu thích của tôi'
    })
