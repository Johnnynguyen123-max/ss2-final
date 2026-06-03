from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..models import Profile
from ..forms import UserUpdateForm, ProfileUpdateForm


# ── ĐĂNG KÝ ──────────────────────────────────────────────────────────────────
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
                username=email, email=email, password=password, first_name=full_name
            )
            Profile.objects.get_or_create(user=user)
            messages.success(request, 'Đăng ký thành công! Mời bạn đăng nhập.')
            return redirect('login')
        else:
            return render(request, 'app/signup.html', {'error': 'Mật khẩu xác nhận không khớp'})

    return render(request, 'app/signup.html')


# ── ĐĂNG NHẬP ────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        email_input = request.POST.get('username')
        password_input = request.POST.get('password')

        try:
            user = User.objects.get(username=email_input)
            if user.check_password(password_input):
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                auth_login(request, user)
                if user.groups.filter(name='Staff').exists() or user.is_superuser:
                    return redirect('manage_orders')
                return redirect('home')
            else:
                return render(request, 'app/login.html', {'error': 'Mật khẩu không chính xác'})
        except User.DoesNotExist:
            return render(request, 'app/login.html', {'error': 'Tài khoản Email này không tồn tại'})

    return render(request, 'app/login.html')


# ── ĐĂNG XUẤT ────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('home')


# ── HỒ SƠ ────────────────────────────────────────────────────────────────────
@login_required
def profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)

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

    return render(request, 'app/profile.html', {'u_form': u_form, 'p_form': p_form})
