# config.py
"""
系統配置檔案
包含 Google Sheets 設定、欄位映射和 UI 選項
"""

# ==================== Google Sheets 設定 ====================
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_ID = '1QXvbW8c8yTFA9BxErpbSDaCEKMcXA69M6TxGSPDeuFU'

# ==================== 工作表名稱 ====================
SHEET_NAMES = {
    'boxes': '物料總覽表',
    'items': '物品明細清單',
    'transactions': '交易/異動紀錄'
}

# ==================== 欄位映射表 ====================
# 定義標準欄位名稱與 Google Sheets 可能使用的欄位名稱的對應關係
FIELD_MAPPING = {
    'boxes': {
        'BoxID': ['BoxID', '容器/專案編號', '容器編號', '專案編號'],
        'Category': ['Category', '類別'],
        'Description': ['Description', '名稱/敘述', '描述', '敘述'],
        'Owner': ['Owner', '負責人', '使用人'],
        'Status': ['Status', '狀態'],
        'CreateDate': ['CreateDate', '建立日期', '創建日期']
    },
    'items': {
        'SN': ['SN', '序號', '物品序號'],
        'ItemName': ['ItemName', '商品名稱', '項目名稱', '物品名稱'],
        'Spec': ['Spec', '規格型號', '規格'],
        'Location': ['Location', '存放位置', '位置'],
        'BoxID': ['BoxID', '所屬編號', '容器編號'],
        'Quantity': ['Quantity', '庫存數量', '數量'],
        'UpdateTime': ['UpdateTime', '更新時間']
    },
    'transactions': {
        'LogID': ['LogID', '紀錄編號', '記錄編號'],
        'BoxID': ['BoxID', '所屬編號', '容器編號'],
        'SN': ['SN', '物品序號', '序號'],
        'ActionType': ['ActionType', '異動類型', '動作類型'],
        'TransQty': ['TransQty', '異動數量', '數量'],
        'Operator': ['Operator', '操作人員', '操作員'],
        'Remark': ['Remark', '備註', '說明'],
        'Timestamp': ['Timestamp', '交易時間', '時間']
    }
}

# ==================== UI 選項配置 ====================
# Box 相關選項
CATEGORY_OPTIONS = ["一般物料", "專案代碼", "維修件", "電腦主機", "其他"]
STATUS_OPTIONS = ["使用中", "空閒", "已結案"]

# 交易類型選項 (完整版)
ACTION_TYPE_OPTIONS = {
    'all': ["入庫", "出庫", "調撥出庫", "調撥入庫", "報廢"],
    'simple': ["入庫", "出庫", "報廢"],  # 簡易交易表單使用
    'transfer': ["調撥出庫", "調撥入庫"]  # 調撥專用
}

# 整合的 UI 選項字典 (向下相容)
UI_OPTIONS = {
    'box_categories': CATEGORY_OPTIONS,
    'box_statuses': STATUS_OPTIONS,
    'transaction_types': ACTION_TYPE_OPTIONS['all'],
    'simple_transaction_types': ACTION_TYPE_OPTIONS['simple'],
    'transfer_types': ACTION_TYPE_OPTIONS['transfer']
}

# ==================== 系統設定 ====================
# 除錯模式
DEBUG_MODE = False

# 每頁顯示筆數
ITEMS_PER_PAGE = 50

# 日期格式
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# 匯出檔案名稱前綴
EXPORT_PREFIX = {
    'boxes': 'boxes_export',
    'items': 'items_export',
    'transactions': 'transactions_export',
    'all': 'material_data_export'
}

# ==================== 驗證規則 ====================
VALIDATION_RULES = {
    'box_id': {
        'min_length': 3,
        'max_length': 50,
        'pattern': r'^[A-Z0-9\-]+
,  # 只允許大寫字母、數字、連字號
        'message': 'BoxID 格式: 大寫字母、數字、連字號,長度 3-50'
    },
    'item_sn': {
        'min_length': 3,
        'max_length': 50,
        'pattern': r'^[A-Z0-9\-]+
,
        'message': 'SN 格式: 大寫字母、數字、連字號,長度 3-50'
    },
    'quantity': {
        'min': 0,
        'max': 999999,
        'message': '數量範圍: 0-999999'
    }
}

# ==================== 樣式配置 ====================
# 顏色主題
COLOR_THEME = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#10b981',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'info': '#3b82f6'
}

# 圖示配置
ICONS = {
    'box': '📦',
    'item': '📜',
    'transaction': '📝',
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑️',
    'search': '🔍',
    'export': '📥',
    'import': '📤',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'transfer_out': '📤',
    'transfer_in': '📥',
    'storage': '📊'
}