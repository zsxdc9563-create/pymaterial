# 物料管理系統 - 模組化重構版

## 📁 專案結構

```
material_management/
├── app.py                  # 主程式入口
├── config.py              # 配置檔案（Google Sheets 設定、欄位映射）
├── gsheet_utils.py        # Google Sheets 連線與操作工具
├── ui_components.py       # UI 元件（CSS、顯示函數）
├── data_operations.py     # 資料操作與業務邏輯
└── README.md              # 專案說明文件
```

## 🔧 模組說明

### 1. `config.py` - 配置檔案
- Google Sheets 連線設定（SCOPES, SPREADSHEET_ID）
- 工作表名稱對應（SHEET_NAMES）
- 欄位映射表（FIELD_MAPPING）
- 下拉選項常數（CATEGORY_OPTIONS, STATUS_OPTIONS 等）

### 2. `gsheet_utils.py` - Google Sheets 工具
- `init_gsheet_connection()` - 初始化連線
- `load_sheet_data()` - 通用資料讀取
- `append_to_sheet()` - 通用資料寫入
- `update_item_quantity()` - 更新庫存
- `get_next_log_id()` - **修正 ValueError 的關鍵函數**

### 3. `ui_components.py` - UI 元件
- `apply_custom_css()` - 應用樣式
- `display_message()` - 顯示訊息
- `display_debug_info()` - 顯示除錯資訊
- `display_metrics()` - 顯示統計指標
- `display_sidebar_stats()` - 側邊欄統計

### 4. `data_operations.py` - 資料操作
- `add_new_box()` - 新增 Box
- `add_new_item()` - 新增物品
- `execute_transaction()` - 執行交易
- `filter_items()` - 過濾物品
- `get_item_options()` / `get_box_options()` - 獲取選項列表

### 5. `app.py` - 主程式
- 頁面配置與初始化
- Session state 管理
- UI 版面配置
- 各功能區塊的串接

## 🐛 Bug 修正

### 原始錯誤
```python
# 錯誤代碼
max_log_id = max([t.get('LogID', 0) for t in st.session_state.transactions_data if t.get('LogID')])
# 當列表為空時會拋出 ValueError
```

### 修正方案
在 `gsheet_utils.py` 中的 `get_next_log_id()` 函數：

```python
def get_next_log_id(transactions_data):
    """計算下一個 LogID，修正空列表錯誤"""
    if not transactions_data:
        return 1
    
    valid_log_ids = [t.get('LogID', 0) for t in transactions_data if t.get('LogID')]
    
    if not valid_log_ids:
        return 1
    
    return max(valid_log_ids) + 1
```

## 🚀 安裝與執行

### 1. 安裝依賴套件
```bash
pip install streamlit pandas gspread google-auth
```

### 2. 設定 Streamlit Secrets
建立 `.streamlit/secrets.toml` 檔案：

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

### 3. 修改 SPREADSHEET_ID
在 `config.py` 中更新你的 Google Sheets ID：

```python
SPREADSHEET_ID = 'your-spreadsheet-id'
```

### 4. 執行應用程式
```bash
streamlit run app.py
```

## 📝 維護指南

### 新增功能時的步驟

1. **新增配置項目** → 修改 `config.py`
2. **新增資料操作** → 修改 `data_operations.py`
3. **新增 UI 元件** → 修改 `ui_components.py`
4. **串接到主程式** → 修改 `app.py`

### 除錯技巧

1. 點擊「🔍 顯示除錯資訊」按鈕
2. 查看「實際標題列」確認 Google Sheets 欄位名稱
3. 查看「欄位映射檢查」確認映射是否正確
4. 必要時在 `config.py` 的 `FIELD_MAPPING` 中新增欄位別名

## ✅ 模組化的優點

1. **易於維護** - 每個模組職責單一，修改時不影響其他部分
2. **易於測試** - 可以單獨測試每個模組的功能
3. **易於擴展** - 新增功能時只需修改相關模組
4. **易於閱讀** - 代碼結構清晰，容易理解
5. **避免重複** - 共用函數集中管理

## 🔄 未來改進方向

- [ ] 加入單元測試
- [ ] 加入日誌記錄功能
- [ ] 加入資料驗證機制
- [ ] 加入批次操作功能
- [ ] 加入資料匯入功能
- [ ] 加入權限管理