from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout

def home(request):
    return render(request, 'app/home.html')

# ĐĂNG KÝ: Lưu mật khẩu thô
def signup(request):
    if request.method == 'POST':
        # 1. In toàn bộ dữ liệu nhận từ Form ra màn hình đen (Terminal)
        print("--- Dữ liệu nhận từ Form ---")
        print(request.POST) 

        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            if User.objects.filter(username=email).exists():
                print("LỖI: Email đã tồn tại trong DB")
                return render(request, 'app/signup.html', {'error': 'Email này đã tồn tại'})
            
            user = User(username=email, email=email, first_name=full_name)
            user.password = password
            user.save()
            
            print(f"THÀNH CÔNG: Đã lưu User {email} với mật khẩu thô là {password}")
            return redirect('login')
        else:
            print(f"LỖI: Mật khẩu không khớp! ({password} vs {confirm_password})")
            return render(request, 'app/signup.html', {'error': 'Mật khẩu không khớp'})
            
    return render(request, 'app/signup.html')

# ĐĂNG NHẬP: Kiểm tra mật khẩu thô
def login_view(request): 
    if request.method == 'POST':
        email_input = request.POST.get('username') 
        password_input = request.POST.get('password')

        try:
            user = User.objects.get(username=email_input)
            
            # So sánh mật khẩu thô
            if user.password == password_input:
                # Gán backend thủ công để Django chấp nhận login mà không cần băm (hashing)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                
                return redirect('home') # Bây giờ nó sẽ nhảy vào trang chủ
            else:
                return render(request, 'app/login.html', {'error': 'Sai mật khẩu'})
        except User.DoesNotExist:
            return render(request, 'app/login.html', {'error': 'Tài khoản không tồn tại'})
            
    return render(request, 'app/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')