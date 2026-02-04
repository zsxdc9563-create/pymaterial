from django.contrib import admin
from django.urls import path, include


# -----------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('material/', include('material_app.urls')),   # Material app 的所有 URL
    #path('', include('material_app.urls')),  # 根路徑也導向 material app


   ]