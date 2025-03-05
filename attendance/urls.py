from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login_view'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/', views.check_out, name='check_out'),
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path("generate-qr/",views.generate_qr, name="generate_qr"),    
    path('profile/', views.profile_view, name='profile'),
    
]

