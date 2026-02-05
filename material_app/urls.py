# material_app/urls.py
from django.urls import path
from . import views

app_name = 'material'

urlpatterns = [

    # # 認證相關
    path("login/", views.api_login, name="login"), # 假設你的 views 裡叫 login_view
    path('logout/', views.api_logout, name='logout'), # 確保名稱是 logout




    # 容器 CRUD
    path("boxes/", views.box_list, name="box_list"),
    path("boxes/add/", views.box_add, name="box_add"),
    path("boxes/checkin/", views.box_checkin, name="box_checkin"),
    path("boxes/toggle-lock/", views.box_toggle_lock, name="box_toggle_lock"),
    path("boxes/<str:box_id>/edit/", views.box_edit, name="box_edit"),
    path("boxes/<str:box_id>/delete/", views.box_delete, name="box_delete"),


    # 物品 CRUD
    path("items/", views.item_list, name="item_list"),
    path("items/add/", views.item_add, name="item_add"),
    path("items/<str:item_id>/edit/", views.item_edit, name="item_edit"),
    path("items/<str:item_id>/delete/", views.item_delete, name="item_delete"),

    # 交易
    path("transaction/transfer/", views.transaction_transfer, name="transaction_transfer"),
    path("transaction/history/", views.transaction_history, name="transaction_history"),

    # API
    path('api/box/<str:box_id>/items/', views.get_box_items, name='get_box_items'),
    path('api/recent-transfers/', views.get_recent_transfers, name='get_recent_transfers'),  # 新增
    # API - 獲取使用者列表
    path('api/users/', views.get_users_list, name='get_users_list'),

]