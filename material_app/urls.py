# material_app/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import box_views, material_views, transaction_views

app_name = 'material'

urlpatterns = [

    # ════════════════════════════════════════════════════════
    # 認證路由
    # ════════════════════════════════════════════════════════
    path('login/',  auth_views.LoginView.as_view(template_name='material/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/material/login/'),       name='logout'),


    # ════════════════════════════════════════════════════════
    # 頁面路由（回傳 HTML）
    # ════════════════════════════════════════════════════════

    # ── 首頁 ──────────────────────────────────────────────────
    path('', box_views.index, name='index'),

    # ── Box 頁面 ─────────────────────────────────────────────
    path('boxes/',                      box_views.box_list,              name='box_list'),
    path('boxes/add/',                  box_views.box_add,               name='box_add'),
    path('boxes/checkin/',              box_views.box_checkin,           name='box_checkin'),
    path('boxes/toggle-lock/',          box_views.box_toggle_lock,       name='box_toggle_lock'),
    path('boxes/export/',               box_views.box_export_excel,      name='box_export_excel'),
    path('boxes/import/',               box_views.box_import_excel,      name='box_import_excel'),
    path('boxes/template/',             box_views.box_download_template, name='box_download_template'),
    path('boxes/<str:box_id>/edit/',    box_views.box_edit,              name='box_edit'),
    path('boxes/<str:box_id>/delete/',  box_views.box_delete,            name='box_delete'),
    path('boxes/<str:box_id>/bom/',     box_views.box_bom,               name='box_bom'),

     # ── Box 頁面 ──專案BOM───────────────────────────────────────────
    path('projects/',                   box_views.project_list,          name='project_list'), 



    # ── Material 頁面 ─────────────────────────────────────────
    # ⚠️ 固定路由（out/add）必須在動態路由 <str:sn> 前面
    path('materials/',                  material_views.material_list,    name='material_list'),
    path('materials/add/',              material_views.material_add,     name='material_add'),
    path('materials/out/',              material_views.material_out,     name='material_out'),
    path('materials/<str:sn>/edit/',    material_views.material_edit,    name='material_edit'),
    path('materials/<str:sn>/delete/',  material_views.material_delete,  name='material_delete'),

    # ── Transaction 頁面 ──────────────────────────────────────
    path('transaction/transfer/',       transaction_views.transaction_transfer, name='transaction_transfer'),
    path('transaction/history/',        transaction_views.transaction_history,  name='transaction_history'),


    # ════════════════════════════════════════════════════════
    # API 路由（回傳 JSON，統一加 /api/ 前綴）
    # ════════════════════════════════════════════════════════

    path('api/boxes/',              box_views.api_box_list,                 name='api_box_list'),
    path('api/boxes/<str:id>/',     box_views.api_box_detail,               name='api_box_detail'),
    path('api/materials/',          material_views.api_material_list,       name='api_material_list'),
    path('api/materials/out/',      material_views.api_material_out,        name='api_material_out'),
    path('api/materials/<str:id>/', material_views.api_material_detail,     name='api_material_detail'),
    path('api/transactions/',       transaction_views.api_transaction_list, name='api_transaction_list'),
]