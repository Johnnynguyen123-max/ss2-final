import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Profile, Book ,Category,Order,OrderItem,Comment,OrderTracking
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q,Case,When





from django.views.decorators.http import require_POST, require_GET
 
from .models import ChatSession, ChatMessage 
try:
    from .forms import UserUpdateForm, ProfileUpdateForm
except ImportError:
    pass 

# --- TRANG CHỦ ---
# views.py
from datetime import datetime

def home(request):
    # 1. Lấy tham số từ URL
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    filter_type = request.GET.get('filter')
    price_range = request.GET.get('price_range')
    year = request.GET.get('year')
    
    # 2. Khởi tạo QuerySet gốc và Danh sách năm
    books = Book.objects.all()
    current_year = datetime.now().year
    # Tạo danh sách 6 năm gần nhất để hiển thị trên UI
    year_choices = range(current_year, current_year - 6, -1)

    # 3. Áp dụng các bộ lọc (Filter)
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        )

    if category_id:
        books = books.filter(category_id=category_id)

    if filter_type == 'new':
        last_90_days = timezone.now() - timedelta(days=90)
        books = books.filter(release_date__gte=last_90_days)

    elif filter_type == 'sale':
        # Lọc sách đang giảm giá
        # Nếu model Book có trường is_on_sale: books = books.filter(is_on_sale=True)
        # Tạm thời sắp xếp theo giá tăng dần để không ra trang trống
        books = books.order_by('price')

    elif filter_type == 'bestseller':
        # Lọc sách bán chạy
        # Nếu model Book có trường sold_count: books = books.order_by('-sold_count')
        # Tạm thời sắp xếp theo ngày phát hành cũ nhất
        books = books.order_by('release_date')

    elif filter_type == 'combo':
        # Hiển thị toàn bộ sách (bổ sung logic combo sau nếu cần)
        books = books.order_by('-release_date')

    if price_range:
        if price_range == "0-100000":
            books = books.filter(price__lt=100000)
        elif price_range == "100000-300000":
            books = books.filter(price__gte=100000, price__lte=300000)
        elif price_range == "300000-max":
            books = books.filter(price__gt=300000)

    # Lọc theo năm phát hành (Chỉ lọc nếu người dùng có chọn)
    if year:
        if year == 'older':
            # Lọc các sách trước năm thấp nhất trong list (ví dụ trước 2021)
            books = books.filter(release_date__year__lt=current_year - 5)
        else:
            books = books.filter(release_date__year=year)

    # 4. SẮP XẾP
    books = books.order_by('-release_date')

    # 5. XỬ LÝ WISHLIST
    favorite_book_ids = []
    if request.user.is_authenticated:
        favorite_book_ids = Book.objects.filter(wishlist=request.user).values_list('id', flat=True)

    # 6. Lấy dữ liệu bổ trợ cho giao diện
    categories = Category.objects.all()
    viewed_ids = request.session.get('recently_viewed', [])
    
    recently_viewed_books = []
    if viewed_ids:
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(viewed_ids)])
        recently_viewed_books = Book.objects.filter(id__in=viewed_ids).order_by(preserved)
    
    context = {
        'books': books,
        'categories': categories,
        'year_choices': year_choices,
        'favorite_book_ids': favorite_book_ids,
        'query': query,
        'is_new_filter': filter_type == 'new',
        'filter_type': filter_type,          # ← để home.html render tiêu đề đúng
        'recently_viewed_books': recently_viewed_books,
        'selected_price': price_range,
        'selected_year': year,
    }
    
    return render(request, 'app/home.html', context)

# --- ĐĂNG KÝ ---
def signup(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            if User.objects.filter(username=email).exists():
                return render(request, 'app/signup.html', {'error': 'Email này đã được đăng ký rồi!'})
            
            user = User.objects.create_user(
                username=email, 
                email=email, 
                password=password,
                first_name=full_name
            )
            
            Profile.objects.get_or_create(user=user)
            messages.success(request, 'Đăng ký thành công! Mời bạn đăng nhập.')
            return redirect('login')
        else:
            return render(request, 'app/signup.html', {'error': 'Mật khẩu xác nhận không khớp'})
            
    return render(request, 'app/signup.html')

# --- ĐĂNG NHẬP ---
def login_view(request): 
    if request.method == 'POST':
        email_input = request.POST.get('username') 
        password_input = request.POST.get('password')
        
        try:
            user = User.objects.get(username=email_input)
            if user.check_password(password_input):
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                
                # --- PHẦN SỬA ĐỔI Ở ĐÂY ---
                # Kiểm tra nếu user là Staff hoặc Superuser
                if user.groups.filter(name='Staff').exists() or user.is_superuser:
                    return redirect('manage_orders') # Thay bằng name url quản lý đơn hàng của Đăng
                
                # Nếu là khách hàng bình thường
                return redirect('home')
                # --------------------------
                
            else:
                return render(request, 'app/login.html', {'error': 'Mật khẩu không chính xác'})
        except User.DoesNotExist:
            return render(request, 'app/login.html', {'error': 'Tài khoản Email này không tồn tại'})
            
    return render(request, 'app/login.html')

# --- ĐĂNG XUẤT ---
def logout_view(request):
    logout(request)
    return redirect('home')

# --- HỒ SƠ CÁ NHÂN ---
@login_required
def profile(request):
    user_profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Hồ sơ đã được cập nhật!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=user_profile)

    context = {'u_form': u_form, 'p_form': p_form}
    return render(request, 'app/profile.html', context)

# --- XỬ LÝ YÊU THÍCH (API) ---
@login_required
def toggle_wishlist(request):
    if request.method == 'POST':
        try:
            # Đọc dữ liệu JSON gửi từ Fetch API
            data = json.loads(request.body)
            book_id = data.get('book_id')
            
            if not book_id:
                return JsonResponse({'status': 'error', 'message': 'Thiếu ID sách'}, status=400)
            
            # Lấy đối tượng Book hoặc trả về 404 nếu không tìm thấy
            book = get_object_or_404(Book, id=book_id)
            user = request.user
            
            # Kiểm tra xem user đã yêu thích sách này chưa
            # Giả định trong Model Book bạn đặt: wishlist = models.ManyToManyField(User, related_name='wishlist_books')
            if book.wishlist.filter(id=user.id).exists():
                book.wishlist.remove(user)
                action = 'removed'
                is_favorite = False
            else:
                book.wishlist.add(user)
                action = 'added'
                is_favorite = True
                
            return JsonResponse({
                'status': 'success', 
                'action': action, 
                'is_favorite': is_favorite
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dữ liệu không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Yêu cầu không hợp lệ'}, status=405)

from .models import Book

def book_detail(request, book_id): # Đổi id thành book_id ở đây
    # 1. Lấy thông tin sách từ Database
    book = get_object_or_404(Book, id=book_id)
    
    # 2. Lấy sách cùng thể loại
    related_books = Book.objects.filter(category=book.category).exclude(id=book_id)[:5]
    
    # --- LOGIC RECENTLY VIEWED (Dùng book_id) ---
    if 'recently_viewed' not in request.session:
        request.session['recently_viewed'] = []
    
    recently_viewed = request.session['recently_viewed']
    
    if book_id in recently_viewed:
        recently_viewed.remove(book_id)
    
    recently_viewed.insert(0, book_id)
    request.session['recently_viewed'] = recently_viewed[:6]
    request.session.modified = True 
    # --------------------------------------------

    # Giữ nguyên các phần khác...
    comments = book.comments.all().order_by('-created_at')
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = book.wishlist.filter(id=request.user.id).exists()
        
    context = {
        'book': book,
        'comments': comments,
        'is_favorite': is_favorite,
        'related_books': related_books,
    }
    return render(request, 'app/book_detail.html', context)
from django.http import JsonResponse

def add_to_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        quantity = int(request.POST.get('quantity', 1))
        
        str_id = str(book_id)
        # Cộng dồn số lượng
        cart[str_id] = cart.get(str_id, 0) + quantity
        
        request.session['cart'] = cart
        request.session.modified = True # Bắt buộc có dòng này để Django lưu Session
        
        # Tính tổng tất cả món hàng để trả về cho Frontend
        total_items = sum(cart.values())
        
        return JsonResponse({
            'status': 'success',
            'total_items': total_items
        })
    return JsonResponse({'status': 'error'}, status=400)
    
    
# views.py
def cart_detail(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    
    # Duyệt qua giỏ hàng trong session để lấy thông tin sách từ DB
    for book_id, quantity in cart.items():
        book = get_object_or_404(Book, id=book_id)
        subtotal = book.price * quantity
        total_price += subtotal
        cart_items.append({
            'book': book,
            'quantity': quantity,
            'subtotal': subtotal
        })
        
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'app/cart.html', context)
def update_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        action = request.POST.get('action') # 'increase' hoặc 'decrease'
        str_id = str(book_id)

        if str_id in cart:
            if action == 'increase':
                cart[str_id] += 1
            elif action == 'decrease':
                cart[str_id] -= 1
                if cart[str_id] < 1: cart[str_id] = 1
            
            request.session['cart'] = cart
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def remove_from_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        str_id = str(book_id)
        
        if str_id in cart:
            del cart[str_id]
            request.session['cart'] = cart
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
@login_required
def wishlist_list(request):
    # Lấy tất cả sách mà user hiện tại nằm trong trường ManyToMany 'wishlist'
    favorite_books = Book.objects.filter(wishlist=request.user).order_by('-id')
    
    context = {
        'books': favorite_books,
        'title': 'Sách yêu thích của tôi'
    }
    return render(request, 'app/wishlist.html', context)
@login_required
def order_history(request):
    # Lấy danh sách đơn hàng của user, sắp xếp theo thời gian mới nhất
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app/order_history.html', {'orders': orders})

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # Chỉ cho xóa nếu đơn hàng chưa được giao (tùy logic của Đăng)
    order.delete()
    messages.success(request, "Đã xóa đơn hàng thành công!")
    return redirect('order_history')

@login_required
def update_order_info(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.full_name = request.POST.get('full_name')
        order.phone = request.POST.get('phone')
        order.address = request.POST.get('address')
        order.save()
        messages.success(request, "Đã cập nhật thông tin đơn hàng!")
    return redirect('order_history')
@login_required
def checkout(request):
    cart_session = request.session.get('cart', {})
    if not cart_session:
        messages.warning(request, "Giỏ hàng của bạn đang trống!")
        return redirect('cart_detail')

    cart_items = []
    total_bill = 0
    for book_id, quantity in cart_session.items():
        book = get_object_or_404(Book, id=book_id)
        subtotal = book.price * quantity
        total_bill += subtotal
        cart_items.append({'book': book, 'quantity': quantity, 'subtotal': subtotal})

    # Lấy thông tin gợi ý từ Profile
    user_profile = getattr(request.user, 'profile', None)
    initial_full_name = f"{request.user.last_name} {request.user.first_name}".strip()
    if not initial_full_name:
        initial_full_name = request.user.username
    initial_phone = user_profile.phone if user_profile else ""
    initial_address = user_profile.address if user_profile else ""

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        # Kiểm tra dữ liệu đầu vào
        if not all([full_name, phone, address]):
            messages.error(request, "Vui lòng điền đầy đủ thông tin giao hàng!")
            return render(request, 'app/checkout.html', {
                'items': cart_items, 'total_bill': total_bill,
                'full_name': full_name, 'phone': phone, 'address': address
            })

        # Regex số điện thoại Việt Nam
        if not re.match(r"^(0[35789])[0-9]{8}$", phone):
            messages.error(request, "Số điện thoại không đúng định dạng Việt Nam!")
            return render(request, 'app/checkout.html', {
                'items': cart_items, 'total_bill': total_bill,
                'full_name': full_name, 'phone': phone, 'address': address
            })

        # Thực hiện lưu đơn hàng
        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address=address,
            total_price=total_bill
        )
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                book=item['book'],
                quantity=item['quantity'],
                price=item['book'].price
            )

        # Xóa giỏ hàng và lưu session
        request.session['cart'] = {}
        request.session.modified = True
        
        # Tin nhắn này sẽ kích hoạt SweetAlert2 ở checkout.html
        messages.success(request, f"Chúc mừng {full_name}, đơn hàng đã được hệ thống tiếp nhận!")
        
        # Quan trọng: Redirect lại chính trang checkout để script SweetAlert2 bắt được message
        return render(request, 'app/checkout.html', {'items': [], 'total_bill': 0})

    return render(request, 'app/checkout.html', {
        'items': cart_items, 
        'total_bill': total_bill,
        'full_name': initial_full_name, 
        'phone': initial_phone,
        'address': initial_address
    })
@login_required
def post_comment(request, book_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        rating = request.POST.get('rating', 5) # Lấy giá trị rating từ form, mặc định là 5
        if content:
            book = get_object_or_404(Book, id=book_id)
            Comment.objects.create(
                book=book,
                user=request.user,
                content=content,
                rating=int(rating) # Lưu số sao vào DB
            )
    return redirect('book_detail', book_id=book_id)
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    book_id = comment.book.id
    
    # Kiểm tra quyền: Chỉ chủ nhân bình luận hoặc admin mới được xóa
    if request.user == comment.user or request.user.is_superuser:
        comment.delete()
        messages.success(request, "Đã xóa bình luận thành công.")
    else:
        messages.error(request, "Bạn không có quyền xóa bình luận này.")
        
    return redirect('book_detail', book_id=book_id)
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Logic Steam: Ưu tiên bắt đầu bằng từ khóa
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
    return JsonResponse({'results': results})
def is_staff(user):
    return user.groups.filter(name='Staff').exists() or user.is_superuser
@user_passes_test(is_staff)
def manage_orders(request):
    # Lấy tất cả đơn hàng, đơn mới nhất lên đầu
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'app/manage_orders.html', {'orders': orders})
@user_passes_test(is_staff)
def confirm_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = 'Confirmed'
    order.save()
    return redirect('manage_orders')
@user_passes_test(is_staff)
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Chỉ cho phép hủy nếu đơn chưa hoàn thành hoặc chưa giao
    if order.status != 'Delivered':
        order.status = 'Cancelled'
        order.save()
    return redirect('manage_orders')
@login_required
def order_tracking(request, order_id):
    # Lấy đơn hàng của đúng user đó, nếu không có hoặc không phải của user thì báo 404
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # Lấy danh sách các sản phẩm trong đơn hàng (OrderItem)
    order_items = order.items.all() 
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'app/order_tracking.html', context)
def pack_and_ship(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        unit = request.POST.get('shipping_unit')
        
        order.status = 'Shipped'
        order.shipping_unit = unit
        order.save()
        
        # Thêm dòng này để Tracking hiển thị "Đang giao"
        OrderTracking.objects.create(
            order=order,
            status='Shipped',
            message=f'Đơn hàng đã được bàn giao cho đơn vị vận chuyển: {unit}.'
        )
    return redirect('manage_orders')
def confirm_received(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Shipped':
        order.status = 'Received'
        order.save()
        
        OrderTracking.objects.create(
            order=order,
            status='Received',
            message='Giao hàng thành công. Người mua đã xác nhận nhận hàng.'
        )
    return redirect('order_history')
def staff_order_detail(request, order_id):
    # Đảm bảo chỉ staff mới được xem
    if not request.user.is_staff:
        return redirect('home')
    
    order = get_object_or_404(Order, id=order_id)
    # Lấy tất cả các sản phẩm có trong đơn hàng này
    items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'items': items,
    }
    return render(request, 'app/staff_order_detail.html', context)  
def staff_book_list(request):
    books = Book.objects.all()
    return render(request, 'app/staff_book_list.html', {'books': books})



def staff_book_insert(request):
    if request.method == "POST":
        # 1. Lấy dữ liệu từ POST
        title = request.POST.get('title')
        author = request.POST.get('author')
        price = request.POST.get('price')
        stock = request.POST.get('stock', 0)  # Bổ sung lấy số lượng
        category_id = request.POST.get('category')
        release_date = request.POST.get('release_date') or timezone.now().date()
        description = request.POST.get('description')
        
        # 2. Lấy file ảnh
        image = request.FILES.get('image')

        # 3. Lấy category object
        category = Category.objects.get(id=category_id) if category_id else None
        
        # 4. Tạo sách mới (Đã bỏ Wishlist)
        new_book = Book.objects.create(
            title=title,
            author=author,
            price=price,
            stock=stock,  # Lưu số lượng vào DB
            category=category,
            release_date=release_date,
            description=description,
            image=image
        )

        # 5. Điều hướng
        if "_addanother" in request.POST:
            return redirect('staff_book_insert')
        return redirect('staff_book_list')

    # GET: Lấy danh sách thể loại để hiện vào select box
    categories = Category.objects.all()
    return render(request, 'app/staff_book_form.html', {'categories': categories})

# app/views.py

def staff_book_update(request, book_id): # Tham số là book_id
    # Sửa id=id thành id=book_id
    book = get_object_or_404(Book, id=book_id) 
    
    if request.method == "POST":
        # Cập nhật các trường dữ liệu
        book.title = request.POST.get('title')
        book.author = request.POST.get('author')
        book.price = request.POST.get('price')
        book.stock = request.POST.get('stock')
        
        category_id = request.POST.get('category')
        book.category = Category.objects.get(id=category_id) if category_id else None
        
        # Lưu thay đổi
        book.save()
        return redirect('staff_book_list')

    # GET: Hiển thị form
    categories = Category.objects.all()
    return render(request, 'app/staff_book_form.html', {
        'book': book, 
        'categories': categories
    })

def staff_book_delete(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        book.delete()
    return redirect('staff_book_list')
@login_required
@require_POST
def customer_send(request):
    """Customer gửi tin nhắn lên."""
    if request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
 
    data = json.loads(request.body)
    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)
 
    session, _ = ChatSession.objects.get_or_create(customer=request.user)
    session.last_message_at = timezone.now()
    session.save(update_fields=['last_message_at'])
 
    msg = ChatMessage.objects.create(session=session, sender=request.user, content=content)
    return JsonResponse({'id': msg.id, 'created_at': msg.created_at.strftime('%H:%M')})
 
 
@login_required
@require_GET
def customer_poll(request):
    """Customer polling lấy tin nhắn.
    - history=1 & after=0 → trả toàn bộ lịch sử (cả tin của customer lẫn staff)
    - bình thường → chỉ trả tin mới hơn after_id
    """
    if request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
 
    after_id = int(request.GET.get('after', 0))
    is_history = request.GET.get('history') == '1'
 
    try:
        session = ChatSession.objects.get(customer=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({'messages': []})
 
    if is_history and after_id == 0:
        # Load toàn bộ lịch sử
        msgs = session.messages.select_related('sender').all()
    else:
        msgs = session.messages.filter(id__gt=after_id).select_related('sender')
 
    # Đánh dấu tin của staff là đã đọc
    session.messages.filter(is_read=False).exclude(
        sender=request.user
    ).update(is_read=True)
 
    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'content': m.content,
                'is_mine': m.sender_id == request.user.id,
                'created_at': m.created_at.strftime('%H:%M'),
            }
            for m in msgs
        ]
    })
 
 
# ──────────────────────────────────────────
#  STAFF endpoints
# ──────────────────────────────────────────
 
@login_required
@require_GET
def staff_sessions(request):
    """Staff lấy danh sách tất cả session + unread count."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
 
    sessions = ChatSession.objects.select_related('customer').prefetch_related('messages')
    result = []
    for s in sessions:
        last = s.last_message()
        result.append({
            'id': s.id,
            'customer_name': s.customer.get_full_name() or s.customer.username,
            'customer_id': s.customer.id,
            'unread': s.unread_for_staff(),
            'last_message': last.content[:60] if last else '',
            'last_time': last.created_at.strftime('%H:%M') if last else '',
        })
 
    total_unread = sum(s['unread'] for s in result)
    return JsonResponse({'sessions': result, 'total_unread': total_unread})
 
 
@login_required
@require_GET
def staff_poll(request, session_id):
    """Staff lấy tin nhắn của 1 session (polling)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
 
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'messages': []})
 
    after_id = int(request.GET.get('after', 0))
 
    if after_id == 0:
        # Lần đầu load: lấy toàn bộ lịch sử
        msgs = session.messages.select_related('sender').all()
    else:
        msgs = session.messages.filter(id__gt=after_id).select_related('sender')
 
    # Đánh dấu tin của customer là đã đọc
    session.messages.filter(sender=session.customer, is_read=False).update(is_read=True)
 
    return JsonResponse({
        'messages': [
            {
                'id': m.id,
                'content': m.content,
                'is_mine': m.sender.is_staff,
                'sender_name': m.sender.get_full_name() or m.sender.username,
                'created_at': m.created_at.strftime('%H:%M'),
            }
            for m in msgs
        ]
    })
 
 
@login_required
@require_POST
def staff_send(request, session_id):
    """Staff gửi tin nhắn trả lời customer."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
 
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session không tồn tại'}, status=404)
 
    data = json.loads(request.body)
    content = data.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Tin nhắn trống'}, status=400)
 
    session.last_message_at = timezone.now()
    session.save(update_fields=['last_message_at'])
 
    msg = ChatMessage.objects.create(session=session, sender=request.user, content=content)
    return JsonResponse({'id': msg.id, 'created_at': msg.created_at.strftime('%H:%M')})