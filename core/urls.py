from django.contrib import admin
from django.urls import path, include

# --- 重點：加入下面這行 ---
from material_app import views 
# -----------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('material/', include('material_app.urls')),
    
    # Auth 相關
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),
    path('api/auth/refresh/', views.api_refresh, name='api_refresh'), # 預留

    # User 相關
    path('api/me/', views.get_me, name='api_me'),

    path('', views.box_list, name='home'),
]