import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Profile, Book 

try:
    from .forms import UserUpdateForm, ProfileUpdateForm
except ImportError:
    pass 

# --- TRANG CHỦ ---
# views.py
def home(request):
    books = Book.objects.all() # Chỉ lấy từ Database
    
    favorite_book_ids = []
    if request.user.is_authenticated:
        favorite_book_ids = request.user.favorite_books.values_list('id', flat=True)
    
    context = {
        'books': books,
        'favorite_book_ids': favorite_book_ids
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
            data = json.loads(request.body)
            book_id = data.get('book_id')
            
            # Sửa lỗi: dùng get_object_or_404 thay vì get_object_or_create
            book = get_object_or_404(Book, id=book_id)
            user = request.user
            
            if book.wishlist.filter(id=user.id).exists():
                book.wishlist.remove(user)
                action = 'removed'
            else:
                book.wishlist.add(user)
                action = 'added'
                
            return JsonResponse({'status': 'success', 'action': action})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
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
def add_to_cart(request, book_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        
        # Lấy quantity từ FormData gửi lên
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
            
        str_id = str(book_id)
        
        # Cộng dồn số lượng vào Session
        if str_id in cart:
            cart[str_id] += quantity
        else:
            cart[str_id] = quantity
            
        request.session['cart'] = cart
        
        # Tính tổng số lượng tất cả sản phẩm để hiển thị cạnh logo
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
