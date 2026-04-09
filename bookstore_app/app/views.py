import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Profile, Book ,Category,Order,OrderItem,Comment
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
try:
    from .forms import UserUpdateForm, ProfileUpdateForm
except ImportError:
    pass 

# --- TRANG CHỦ ---
# views.py
def home(request):
    # 1. Lấy tham số từ URL
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    filter_type = request.GET.get('filter')
    
    # 2. Khởi tạo QuerySet gốc
    books = Book.objects.all()

    # 3. Áp dụng các bộ lọc (Filter)
    # Lọc theo từ khóa tìm kiếm
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        )

    # Lọc theo danh mục
    if category_id:
        books = books.filter(category_id=category_id)

    # Lọc theo sách mới (trong 30 ngày qua)
    if filter_type == 'new':
        last_30_days = timezone.now() - timedelta(days=30)
        books = books.filter(release_date__gte=last_30_days)

    # 4. SẮP XẾP: Luôn đưa sách mới nhất lên đầu
    books = books.order_by('-release_date')

    # 5. XỬ LÝ WISHLIST: Lấy danh sách ID sách đã thích
    favorite_book_ids = []
    if request.user.is_authenticated:
        # Cách an toàn nhất nếu bạn chưa chắc chắn về related_name trong Models
        favorite_book_ids = Book.objects.filter(wishlist=request.user).values_list('id', flat=True)

    # 6. Lấy dữ liệu bổ trợ cho giao diện
    categories = Category.objects.all()
    
    context = {
        'books': books,
        'categories': categories,
        'favorite_book_ids': favorite_book_ids,
        'query': query, # Trả lại để hiển thị trong ô search
        'is_new_filter': filter_type == 'new',
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
                return redirect('home')
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
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Book

# views.py
# views.py
def book_detail(request, book_id):
    # 1. Lấy thông tin sách từ Database
    book = get_object_or_404(Book, id=book_id)
    
    # 2. Lấy danh sách bình luận (hiển thị từ mới đến cũ)
    comments = book.comments.all().order_by('-created_at')
    
    # 3. Logic lấy danh sách ID yêu thích (nếu cần hiển thị nút tim ở trang detail)
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = book.wishlist.filter(id=request.user.id).exists()
    
    context = {
        'book': book,
        'comments': comments,
        'is_favorite': is_favorite,
    }
    # Trả về template HTML thay vì JsonResponse
    return render(request, 'app/book_detail.html', context)

# app/views.py
# views.py
from django.http import JsonResponse

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