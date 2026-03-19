from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'), # Đổi views.login thành views.login_view
    path('signup/', views.signup, name='signup'),
]