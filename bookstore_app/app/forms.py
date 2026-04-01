
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

# Form Đăng Ký (Signup)
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Bắt buộc nhập email chính xác.')
    first_name = forms.CharField(max_length=30, required=False, label='Họ và tên đệm')
    last_name = forms.CharField(max_length=30, required=False, label='Tên')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

# Form Cập nhật thông tin cá nhân (Edit Personal Information)
class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

# Form Đăng nhập (Dùng mặc định AuthenticationForm của Django như code bạn đã viết là ổn)
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'phone']