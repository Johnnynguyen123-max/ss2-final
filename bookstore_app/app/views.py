from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login # Đổi tên khi import để tránh trùng
from django.contrib.auth.forms import AuthenticationForm

def home(request):
    return render(request, 'app/home.html')

# Đổi tên hàm này từ login thành login_view
def login_view(request): 
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user) # Gọi hàm đã đổi tên ở trên
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'app/login.html', {'form': form})

def signup(request):
    # Giữ nguyên logic signup của bạn
    return render(request, 'app/signup.html')