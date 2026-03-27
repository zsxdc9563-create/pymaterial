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

    # ── Box 頁面 ──────────────────────────────────────────────
    path('boxes/',                      box_views.box_list,              name='box_list'),
    path('boxes/add/',                  box_views.box_add,               name='box_add'),
    path('boxes/checkin/',              box_views.box_checkin,           name='box_checkin'),
    path('boxes/toggle-lock/',          box_views.box_toggle_lock,       name='box_toggle_lock'),
    path('boxes/export/',               box_views.box_export_excel,      name='box_export_excel'),
    path('boxes/import/',               box_views.box_import_excel,      name='box_import_excel'),
    path('boxes/template/',             box_views.box_download_template, name='box_download_template'),
    path('boxes/<str:box_id>/',         box_views.box_detail,            name='box_detail'),
    path('boxes/<str:box_id>/edit/',    box_views.box_edit,              name='box_edit'),
    path('boxes/<str:box_id>/delete/',  box_views.box_delete,            name='box_delete'),
    path('boxes/<str:box_id>/bom/',     box_views.box_bom,               name='box_bom'),
    
    # ── 專案 BOM ──────────────────────────────────────────────
    path('projects/', box_views.project_list, name='project_list'),

    # ── Material 頁面 ─────────────────────────────────────────
    # ⚠️ 固定路由（add / out / in / adjust）必須在動態路由 <int:item_id> 前面
    path('materials/',                       material_views.material_list,    name='material_list'),
    path('materials/add/',                   material_views.material_add,     name='material_add'),
    path('materials/out/',                   material_views.material_out_view,    name='material_out'),
    path('materials/in/',                    material_views.material_in_view,     name='material_in'),
    path('materials/adjust/',               material_views.material_adjust_view, name='material_adjust'),
    # 舊版用 <str:sn>，新版改用 <int:item_id>（pk 更精確）
    path('materials/<int:item_id>/edit/',    material_views.material_edit,    name='material_edit'),
    path('materials/<int:item_id>/delete/',  material_views.material_delete,  name='material_delete'),

    # ── Transaction 頁面 ──────────────────────────────────────
    path('transaction/transfer/', transaction_views.transaction_transfer, name='transaction_transfer'),
    path('transaction/history/',  transaction_views.transaction_history,  name='transaction_history'),


    # ════════════════════════════════════════════════════════
    # API 路由（回傳 JSON，統一加 /api/ 前綴）
    # ════════════════════════════════════════════════════════

    # ── Box API ───────────────────────────────────────────────
    # ⚠️ 固定路由必須在動態路由 <str:box_id> 前面
    path('api/boxes/',
         box_views.BoxListCreateAPIView.as_view(),    name='api_box_list'),
    path('api/boxes/<str:box_id>/',
         box_views.BoxDetailAPIView.as_view(),        name='api_box_detail'),
    path('api/boxes/<str:box_id>/lock/',
         box_views.BoxToggleLockAPIView.as_view(),    name='api_box_lock'),
    path('api/boxes/<str:box_id>/shortage/',
         box_views.BoxShortageAPIView.as_view(),      name='api_box_shortage'),

    # ── Material API ──────────────────────────────────────────
    # ⚠️ 固定路由（out / in / adjust）必須在動態路由 <int:item_id> 前面
    path('api/materials/',
         material_views.MaterialListCreateAPIView.as_view(),  name='api_material_list'),
    path('api/materials/<int:item_id>/',
         material_views.MaterialDetailAPIView.as_view(),      name='api_material_detail'),
    path('api/materials/<int:item_id>/out/',
         material_views.MaterialStockOutAPIView.as_view(),    name='api_material_out'),
    path('api/materials/<int:item_id>/in/',
         material_views.MaterialStockInAPIView.as_view(),     name='api_material_in'),
    path('api/materials/<int:item_id>/adjust/',
         material_views.MaterialAdjustAPIView.as_view(),      name='api_material_adjust'),
    path('api/materials/<int:item_id>/shortage/',
         material_views.MaterialShortageAPIView.as_view(),    name='api_material_shortage'),

    # ── Transaction API ───────────────────────────────────────
    path('api/transactions/',
         transaction_views.TransactionListAPIView.as_view(),  name='api_transaction_list'),
    path('api/transactions/stats/',
         transaction_views.TransactionStatsAPIView.as_view(), name='api_transaction_stats'),
    path('api/transactions/transfer/',
         transaction_views.TransferAPIView.as_view(),         name='api_transaction_transfer'),
]