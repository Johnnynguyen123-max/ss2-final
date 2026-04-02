
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Bắt buộc nhập email chính xác.')
    first_name = forms.CharField(max_length=30, required=False, label='Họ và tên đệm')
    last_name = forms.CharField(max_length=30, required=False, label='Tên')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'phone']