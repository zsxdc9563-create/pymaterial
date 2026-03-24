from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
# -----------------------


#---------redirect 是 Django 的內建函式，但不會自動載入，任何東西用之前都要先 import，這是 Python 的基本規則。
# -------lambda 是 Python 的匿名函式，就是一個沒有名字的簡單函式。
urlpatterns = [

    path('admin/', admin.site.urls),
    path('material/', include('material_app.urls')),   # Material app 的所有 URL
    path('', lambda request: redirect('material/')),  # 根路徑自動跳轉
   
   
   
   #path('', include('material_app.urls')),  # 根路徑也導向 material app

   ]