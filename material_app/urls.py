# material_app/urls.py
from django.urls import path
from . import views

app_name = 'material'

urlpatterns = [

    #首頁
    path('', views.index, name='index'),


    #  認證相關
    path("login/", views.api_login, name="login"),
    path("logout/", views.api_logout, name="logout"),
    path('api/me/', views.get_me, name='api_me'),

    # 容器 CRUD - 改為使用 int:box_id
    path("boxes/", views.box_list, name="box_list"),
    path("boxes/add/", views.box_add, name="box_add"),
    path("boxes/checkin/", views.box_checkin, name="box_checkin"),
    path("boxes/toggle-lock/", views.box_toggle_lock, name="box_toggle_lock"),
    path("boxes/<str:box_id>/edit/", views.box_edit, name="box_edit"),
    path("boxes/<str:box_id>/delete/", views.box_delete, name="box_delete"),

    # 物品 CRUD
    path("items/", views.item_list, name="item_list"),
    path("items/add/", views.item_add, name="item_add"),
    path('items/<str:sn>/edit/', views.item_edit, name='item_edit'),
    path('items/<str:sn>/delete/', views.item_delete, name='item_delete'),

    # 交易
    path("transaction/transfer/", views.transaction_transfer, name="transaction_transfer"),
    path("transaction/history/", views.transaction_history, name="transaction_history"),

    # ==================== 交易記錄 API ====================
    path('api/transactions/my/', views.get_my_transactions, name='api_transactions_my'),
    path('api/transactions/all/', views.get_all_transactions, name='api_transactions_all'),

    # API Endpoints
    path('api/box/<str:box_id>/items/', views.get_box_items, name='get_box_items'),
    path('api/box/<str:box_id>/details/', views.get_box_details, name='box_details_api'),#容器詳細資料
    path('api/recent-transfers/', views.get_recent_transfers, name='get_recent_transfers'),
    path('api/users/', views.get_users_list, name='get_users_list'),


    ##所有人都可以看
    path('employee/view/',views.employee_can_view, name='employee_can_view')


]