from datetime import datetime, timedelta

from django.shortcuts import render
from django.db.models import Q, Case, When, Avg
from django.utils import timezone

from ..models import Book, Category, Comment


# ── TRANG CHỦ ────────────────────────────────────────────────────────────────
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    filter_type = request.GET.get('filter')
    price_range = request.GET.get('price_range')
    year = request.GET.get('year')

    books = Book.objects.select_related('category')
    current_year = datetime.now().year
    year_choices = range(current_year, current_year - 6, -1)

    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    if category_id:
        books = books.filter(category_id=category_id)

    if filter_type == 'new':
        last_90_days = timezone.now() - timedelta(days=90)
        books = books.filter(release_date__gte=last_90_days)
    elif filter_type == 'bestseller':
        books = books.order_by('-sold_count')

    if price_range:
        if price_range == "0-100000":
            books = books.filter(price__lt=100000)
        elif price_range == "100000-300000":
            books = books.filter(price__gte=100000, price__lte=300000)
        elif price_range == "300000-max":
            books = books.filter(price__gt=300000)

    if year:
        if year == 'older':
            books = books.filter(release_date__year__lt=current_year - 5)
        else:
            books = books.filter(release_date__year=year)

    books = books.order_by('-release_date')

    favorite_book_ids = []
    if request.user.is_authenticated:
        favorite_book_ids = list(
            Book.objects.filter(wishlist=request.user).values_list('id', flat=True)
        )

    categories = Category.objects.all()

    viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed_books = []
    if viewed_ids:
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(viewed_ids)])
        recently_viewed_books = Book.objects.filter(id__in=viewed_ids).order_by(preserved)

    # Số liệu thực cho hero stats
    avg_rating = Comment.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    new_books_count = Book.objects.filter(
        release_date__gte=timezone.now().date() - timedelta(days=90)
    ).count()

    context = {
        'books': books,
        'categories': categories,
        'year_choices': year_choices,
        'favorite_book_ids': favorite_book_ids,
        'query': query,
        'filter_type': filter_type,
        'recently_viewed_books': recently_viewed_books,
        'selected_price': price_range,
        'selected_year': year,
        'avg_rating': avg_rating,
        'new_books_count': new_books_count,
    }
    return render(request, 'app/home.html', context)


# ── GỢI Ý TÌM KIẾM ───────────────────────────────────────────────────────────
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        from django.http import JsonResponse
        return JsonResponse({'results': []})

    starts_with = Book.objects.filter(title__istartswith=query)
    contains = Book.objects.filter(
        Q(title__icontains=query) | Q(author__icontains=query)
    ).exclude(id__in=starts_with.values_list('id', flat=True))

    books = (list(starts_with) + list(contains))[:5]
    results = []
    for book in books:
        img_url = book.image.url if book.image else '/static/app/images/default.jpg'
        results.append({
            'id': book.id,
            'title': book.title[:50] + '...' if len(book.title) > 50 else book.title,
            'author': book.author,
            'price': "{:,.0f}₫".format(book.price) if book.price else "Free",
            'image': img_url,
        })

    from django.http import JsonResponse
    return JsonResponse({'results': results})
