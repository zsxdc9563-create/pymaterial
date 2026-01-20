import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import gspread
from google.oauth2.service_account import Credentials
import io

# 頁面配置
st.set_page_config(
    page_title="物料管理系統",
    page_icon="📦",
    layout="wide"
)

# Google Sheets 設定
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_ID = '1QXvbW8c8yTFA9BxErpbSDaCEKMcXA69M6TxGSPDeuFU'

# 欄位映射表
FIELD_MAPPING = {
    'boxes': {
        'BoxID': ['BoxID', '容器/專案編號', '容器編號', '專案編號'],
        'Category': ['Category', '類別'],
        'Description': ['Description', '名稱/敘述', '描述', '敘述'],
        'Owner': ['Owner', '負責人'],
        'Status': ['Status', '狀態'],
        'CreateDate': ['CreateDate', '建立日期', '創建日期']
    },
    'items': {
        'SN': ['SN', '序號', '物品序號'],
        'ItemName': ['ItemName', '商品名稱', '物品名稱', '項目名稱'],
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

def find_field_name(row_dict, possible_names):
    """從字典中找到第一個存在的欄位名稱"""
    for name in possible_names:
        if name in row_dict:
            return name
    return None

def normalize_row(row_dict, field_mapping):
    """將一行資料的欄位名稱標準化為英文"""
    normalized = {}
    for standard_name, possible_names in field_mapping.items():
        actual_name = find_field_name(row_dict, possible_names)
        if actual_name:
            value = row_dict[actual_name]
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                try:
                    normalized[standard_name] = int(value) if value != '' else 0
                except (ValueError, TypeError):
                    normalized[standard_name] = 0
            else:
                normalized[standard_name] = str(value) if value else ''
        else:
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                normalized[standard_name] = 0
            else:
                normalized[standard_name] = ''
    return normalized

@st.cache_resource
def init_gsheet_connection():
    """初始化 Google Sheets 連線"""
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet
    except Exception as e:
        st.error(f"Google Sheets 連線失敗: {str(e)}")
        return None

def load_boxes_from_sheet(spreadsheet):
    """從 Sheet 1 讀取物料總覽"""
    try:
        worksheet = spreadsheet.worksheet("物料總覽表")
        data = worksheet.get_all_records()
        
        st.session_state.debug_boxes_raw = data[:3] if data else []
        st.session_state.debug_boxes_headers = worksheet.row_values(1)
        
        if not data:
            return []
        normalized_data = [normalize_row(row, FIELD_MAPPING['boxes']) for row in data]
        return [row for row in normalized_data if row.get('BoxID')]
    except Exception as e:
        st.error(f"讀取物料總覽時發生問題: {str(e)}")
        return []

def load_items_from_sheet(spreadsheet):
    """從 Sheet 2 讀取物品清單"""
    try:
        worksheet = spreadsheet.worksheet("物品明細清單")
        data = worksheet.get_all_records()
        
        st.session_state.debug_items_raw = data[:3] if data else []
        st.session_state.debug_items_headers = worksheet.row_values(1)
        
        if not data:
            return []
        normalized_data = [normalize_row(row, FIELD_MAPPING['items']) for row in data]
        return [row for row in normalized_data if row.get('SN')]
    except Exception as e:
        st.error(f"讀取物品清單時發生問題: {str(e)}")
        return []

def load_transactions_from_sheet(spreadsheet):
    """從 Sheet 3 讀取交易記錄"""
    try:
        worksheet = spreadsheet.worksheet("交易/異動紀錄")
        data = worksheet.get_all_records()
        
        st.session_state.debug_trans_raw = data[:3] if data else []
        st.session_state.debug_trans_headers = worksheet.row_values(1)
        
        if not data:
            return []
        normalized_data = [normalize_row(row, FIELD_MAPPING['transactions']) for row in data]
        return [row for row in normalized_data if row.get('LogID') or row.get('SN')]
    except Exception as e:
        st.error(f"讀取交易記錄時發生問題: {str(e)}")
        return []

def append_box_to_sheet(spreadsheet, box_data):
    """新增一筆 Box 資料到 Sheet 1"""
    try:
        worksheet = spreadsheet.worksheet("物料總覽表")
        headers = worksheet.row_values(1)
        
        row = []
        for header in headers:
            for std_name, possible_names in FIELD_MAPPING['boxes'].items():
                if header in possible_names:
                    row.append(box_data.get(std_name, ''))
                    break
            else:
                row.append('')
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入物料總覽失敗: {str(e)}")
        return False

def append_item_to_sheet(spreadsheet, item_data):
    """新增一筆物品資料到 Sheet 2"""
    try:
        worksheet = spreadsheet.worksheet("物品明細清單")
        headers = worksheet.row_values(1)
        
        row = []
        for header in headers:
            for std_name, possible_names in FIELD_MAPPING['items'].items():
                if header in possible_names:
                    row.append(item_data.get(std_name, ''))
                    break
            else:
                row.append('')
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入物品清單失敗: {str(e)}")
        return False

def append_transaction_to_sheet(spreadsheet, trans_data):
    """新增一筆交易記錄到 Sheet 3"""
    try:
        worksheet = spreadsheet.worksheet("交易/異動紀錄")
        headers = worksheet.row_values(1)
        
        row = []
        for header in headers:
            for std_name, possible_names in FIELD_MAPPING['transactions'].items():
                if header in possible_names:
                    row.append(trans_data.get(std_name, ''))
                    break
            else:
                row.append('')
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入交易記錄失敗: {str(e)}")
        return False

def update_item_quantity(spreadsheet, sn, new_quantity, update_time):
    """更新物品庫存數量"""
    try:
        worksheet = spreadsheet.worksheet("物品明細清單")
        headers = worksheet.row_values(1)
        
        sn_col = None
        qty_col = None
        time_col = None
        
        for i, header in enumerate(headers, 1):
            if header in FIELD_MAPPING['items']['SN']:
                sn_col = i
            elif header in FIELD_MAPPING['items']['Quantity']:
                qty_col = i
            elif header in FIELD_MAPPING['items']['UpdateTime']:
                time_col = i
        
        if not sn_col:
            st.error("找不到序號欄位")
            return False
        
        cell = worksheet.find(sn, in_column=sn_col)
        if cell and qty_col:
            worksheet.update_cell(cell.row, qty_col, new_quantity)
            if time_col:
                worksheet.update_cell(cell.row, time_col, update_time)
            return True
        return False
    except Exception as e:
        st.error(f"更新庫存失敗: {str(e)}")
        return False

def update_box_in_sheet(spreadsheet, box_id, updated_data):
    """更新 Box 資料"""
    try:
        worksheet = spreadsheet.worksheet("物料總覽表")
        headers = worksheet.row_values(1)
        
        boxid_col = None
        for i, header in enumerate(headers, 1):
            if header in FIELD_MAPPING['boxes']['BoxID']:
                boxid_col = i
                break
        
        if not boxid_col:
            return False
        
        cell = worksheet.find(box_id, in_column=boxid_col)
        if cell:
            for i, header in enumerate(headers, 1):
                for std_name, possible_names in FIELD_MAPPING['boxes'].items():
                    if header in possible_names:
                        worksheet.update_cell(cell.row, i, updated_data.get(std_name, ''))
                        break
            return True
        return False
    except Exception as e:
        st.error(f"更新 Box 失敗: {str(e)}")
        return False

def update_item_in_sheet(spreadsheet, sn, updated_data):
    """更新物品資料"""
    try:
        worksheet = spreadsheet.worksheet("物品明細清單")
        headers = worksheet.row_values(1)
        
        sn_col = None
        for i, header in enumerate(headers, 1):
            if header in FIELD_MAPPING['items']['SN']:
                sn_col = i
                break
        
        if not sn_col:
            return False
        
        cell = worksheet.find(sn, in_column=sn_col)
        if cell:
            for i, header in enumerate(headers, 1):
                for std_name, possible_names in FIELD_MAPPING['items'].items():
                    if header in possible_names:
                        worksheet.update_cell(cell.row, i, updated_data.get(std_name, ''))
                        break
            return True
        return False
    except Exception as e:
        st.error(f"更新物品失敗: {str(e)}")
        return False

def delete_box_from_sheet(spreadsheet, box_id):
    """刪除 Box 資料"""
    try:
        worksheet = spreadsheet.worksheet("物料總覽表")
        headers = worksheet.row_values(1)
        
        boxid_col = None
        for i, header in enumerate(headers, 1):
            if header in FIELD_MAPPING['boxes']['BoxID']:
                boxid_col = i
                break
        
        if not boxid_col:
            return False
        
        cell = worksheet.find(box_id, in_column=boxid_col)
        if cell:
            worksheet.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"刪除 Box 失敗: {str(e)}")
        return False

def delete_item_from_sheet(spreadsheet, sn):
    """刪除物品資料"""
    try:
        worksheet = spreadsheet.worksheet("物品明細清單")
        headers = worksheet.row_values(1)
        
        sn_col = None
        for i, header in enumerate(headers, 1):
            if header in FIELD_MAPPING['items']['SN']:
                sn_col = i
                break
        
        if not sn_col:
            return False
        
        cell = worksheet.find(sn, in_column=sn_col)
        if cell:
            worksheet.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"刪除物品失敗: {str(e)}")
        return False

# 初始化連線
spreadsheet = init_gsheet_connection()

# 初始化 session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'boxes_data' not in st.session_state:
    st.session_state.boxes_data = []
if 'items_data' not in st.session_state:
    st.session_state.items_data = []
if 'transactions_data' not in st.session_state:
    st.session_state.transactions_data = []
if 'next_log_id' not in st.session_state:
    st.session_state.next_log_id = 1
if 'show_debug' not in st.session_state:
    st.session_state.show_debug = False

# CSS 樣式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .success-msg {
        padding: 1rem;
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #10b981;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .error-msg {
        padding: 1rem;
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #ef4444;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .info-box {
        padding: 1rem;
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .debug-box {
        padding: 1.5rem;
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border-radius: 12px;
        margin: 1rem 0;
        border: 2px solid #f59e0b;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .filter-section {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .action-section {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    h1, h2, h3 {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size: 2.5rem;">📦 物料管理系統</h1>
    <p style="margin:0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.95;">Google Sheets 整合 | 進階搜尋 | 編輯管理 | 批次匯入匯出</p>
</div>
""", unsafe_allow_html=True)

# 載入資料按鈕
col_load, col_debug, col_info = st.columns([1, 1, 3])
with col_load:
    if st.button("🔄 載入資料", width="stretch"):
        if spreadsheet:
            with st.spinner("載入中..."):
                st.session_state.boxes_data = load_boxes_from_sheet(spreadsheet)
                st.session_state.items_data = load_items_from_sheet(spreadsheet)
                st.session_state.transactions_data = load_transactions_from_sheet(spreadsheet)
            
                if st.session_state.transactions_data:
                    valid_log_ids = [t.get('LogID', 0) for t in st.session_state.transactions_data if t.get('LogID')]
                    if valid_log_ids:
                        st.session_state.next_log_id = max(valid_log_ids) + 1
                    else:
                        st.session_state.next_log_id = 1
                else:
                    st.session_state.next_log_id = 1
                
                st.session_state.data_loaded = True
                st.session_state.message = {'text': '資料載入成功', 'type': 'success'}
                st.rerun()

with col_debug:
    if st.button("🔍 顯示除錯資訊", width="stretch"):
        st.session_state.show_debug = not st.session_state.show_debug

with col_info:
    if st.session_state.data_loaded:
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("📦 Boxes", len(st.session_state.boxes_data))
        with col_b:
            st.metric("📜 Items", len(st.session_state.items_data))
        with col_c:
            st.metric("📝 Logs", len(st.session_state.transactions_data))
    else:
        st.markdown('<div class="info-box">ℹ️ 請點擊「載入資料」按鈕從 Google Sheets 讀取資料</div>', unsafe_allow_html=True)

# 除錯資訊區塊
if st.session_state.show_debug and st.session_state.data_loaded:
    st.markdown('<div class="debug-box">', unsafe_allow_html=True)
    st.subheader("🔍 除錯資訊")
    
    debug_tab1, debug_tab2, debug_tab3 = st.tabs(["物料總覽", "物品清單", "交易紀錄"])
    
    with debug_tab1:
        st.write("**實際標題列:**")
        if hasattr(st.session_state, 'debug_boxes_headers'):
            headers_df = pd.DataFrame([st.session_state.debug_boxes_headers], columns=[f"欄位{i+1}" for i in range(len(st.session_state.debug_boxes_headers))])
            st.dataframe(headers_df, width="stretch")
        
        st.write("**原始資料 (前3筆):**")
        if hasattr(st.session_state, 'debug_boxes_raw') and st.session_state.debug_boxes_raw:
            st.dataframe(pd.DataFrame(st.session_state.debug_boxes_raw), width="stretch")
    
    with debug_tab2:
        st.write("**實際標題列:**")
        if hasattr(st.session_state, 'debug_items_headers'):
            headers_df = pd.DataFrame([st.session_state.debug_items_headers], columns=[f"欄位{i+1}" for i in range(len(st.session_state.debug_items_headers))])
            st.dataframe(headers_df, width="stretch")
        
        st.write("**原始資料 (前3筆):**")
        if hasattr(st.session_state, 'debug_items_raw') and st.session_state.debug_items_raw:
            st.dataframe(pd.DataFrame(st.session_state.debug_items_raw), width="stretch")
        
        st.write("**欄位映射檢查:**")
        if hasattr(st.session_state, 'debug_items_headers') and st.session_state.debug_items_headers:
            mapping_result = {}
            for std_name, possible_names in FIELD_MAPPING['items'].items():
                found = None
                for name in possible_names:
                    if name in st.session_state.debug_items_headers:
                        found = name
                        break
                mapping_result[std_name] = found or "❌ 未找到"
            mapping_df = pd.DataFrame(list(mapping_result.items()), columns=['標準欄位', '對應到的欄位'])
            st.dataframe(mapping_df, width="stretch")
    
    with debug_tab3:
        st.write("**實際標題列:**")
        if hasattr(st.session_state, 'debug_trans_headers'):
            headers_df = pd.DataFrame([st.session_state.debug_trans_headers], columns=[f"欄位{i+1}" for i in range(len(st.session_state.debug_trans_headers))])
            st.dataframe(headers_df, width="stretch")
        
        st.write("**原始資料 (前3筆):**")
        if hasattr(st.session_state, 'debug_trans_raw') and st.session_state.debug_trans_raw:
            st.dataframe(pd.DataFrame(st.session_state.debug_trans_raw), width="stretch")
    
    st.markdown('</div>', unsafe_allow_html=True)

# 顯示訊息
if 'message' in st.session_state and st.session_state.message:
    msg = st.session_state.message
    if msg['type'] == 'success':
        st.markdown(f'<div class="success-msg">✅ {msg["text"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="error-msg">❌ {msg["text"]}</div>', unsafe_allow_html=True)
    st.session_state.message = None

# 導航標籤
tab1, tab2, tab3 = st.tabs(["📦 物料總覽", "📜 物品清單", "📝 交易紀錄"])

# ==================== Tab 1: 物料總覽 ====================
with tab1:
    st.markdown("### 📦 物料總覽表")
    
    # 進階搜尋區域
    with st.expander("🔍 進階搜尋與篩選", expanded=False):
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_boxid = st.text_input("🔎 BoxID 關鍵字", key="search_boxid", placeholder="輸入關鍵字搜尋...")
            categories = list(set([b.get('Category', '') for b in st.session_state.boxes_data if b.get('Category')]))
            filter_category = st.multiselect("📁 類別", ["全部"] + categories, default=["全部"])
        
        with col2:
            owners = list(set([b.get('Owner', '') for b in st.session_state.boxes_data if b.get('Owner')]))
            filter_owner = st.multiselect("👤 負責人", ["全部"] + owners, default=["全部"])
        
        with col3:
            statuses = list(set([b.get('Status', '') for b in st.session_state.boxes_data if b.get('Status')]))
            filter_status = st.multiselect("📊 狀態", ["全部"] + statuses, default=["全部"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 操作按鈕區域
    st.markdown('<div class="action-section">', unsafe_allow_html=True)
    col_add, col_import, col_export, col_template = st.columns(4)
    
    with col_add:
        if st.button("➕ 新增 Box", width="stretch", key="add_box_btn", type="primary"):
            st.session_state.show_box_form = not st.session_state.get('show_box_form', False)
    
    with col_import:
        uploaded_boxes = st.file_uploader("📤 批次匯入", type=['csv'], key="import_boxes", label_visibility="collapsed")
        if uploaded_boxes:
            try:
                df = pd.read_csv(uploaded_boxes, encoding='utf-8-sig')
                success_count = 0
                
                # 顯示匯入預覽
                st.write("📋 匯入預覽:")
                st.dataframe(df.head(), width="stretch")
                
                if st.button("✅ 確認匯入", key="confirm_import_boxes"):
                    for _, row in df.iterrows():
                        box_data = {
                            'BoxID': str(row.get('BoxID', row.get('容器/專案編號', ''))),
                            'Category': str(row.get('Category', row.get('類別', ''))),
                            'Description': str(row.get('Description', row.get('名稱/敘述', ''))),
                            'Owner': str(row.get('Owner', row.get('負責人', ''))),
                            'Status': str(row.get('Status', row.get('狀態', ''))),
                            'CreateDate': str(row.get('CreateDate', row.get('建立日期', datetime.now().strftime('%Y-%m-%d'))))
                        }
                        if box_data['BoxID'] and append_box_to_sheet(spreadsheet, box_data):
                            st.session_state.boxes_data.append(box_data)
                            success_count += 1
                    st.session_state.message = {'text': f'✅ 成功匯入 {success_count} 筆資料', 'type': 'success'}
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 匯入失敗: {str(e)}")
    
    with col_export:
        if st.session_state.boxes_data:
            df_export = pd.DataFrame(st.session_state.boxes_data)
            csv = df_export.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 匯出 CSV",
                data=csv,
                file_name=f"boxes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch"
            )
    
    with col_template:
        template_data = {
            'BoxID': ['BOX-001', 'BOX-002'],
            'Category': ['一般物料', '專案代碼'],
            'Description': ['範例描述1', '範例描述2'],
            'Owner': ['張三', '李四'],
            'Status': ['使用中', '空閒'],
            'CreateDate': ['2026-01-20', '2026-01-20']
        }
        template_df = pd.DataFrame(template_data)
        template_csv = template_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📄 下載模板",
            data=template_csv,
            file_name="boxes_template.csv",
            mime="text/csv",
            width="stretch"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 新增表單
    if st.session_state.get('show_box_form', False):
        with st.form("add_box_form"):
            st.subheader("新增 BoxID")
            col1, col2 = st.columns(2)
            
            with col1:
                box_id = st.text_input("容器/專案編號 (BoxID) *", placeholder="例如: BOX-002")
                # 提供可自訂的類別選項
                category_options = ["一般物料", "專案代碼", "維修件", "電腦主機", "其他"]
                category = st.selectbox("類別 *", category_options)
                # 允許自訂類別
                custom_category = st.text_input("或輸入自訂類別", placeholder="留空則使用上方選項")
                description = st.text_input("名稱/敘述 *", placeholder="輸入描述")
            
            with col2:
                owner = st.text_input("負責人", placeholder="管理人員姓名")
                status = st.selectbox("狀態 *", ["使用中", "空閒", "已結案"])
                create_date = st.date_input("建立日期", value=datetime.now())
            
            col_submit, col_cancel = st.columns([1, 5])
            with col_submit:
                submitted = st.form_submit_button("提交", width="stretch")
            with col_cancel:
                cancelled = st.form_submit_button("取消", width="stretch")
            
            if submitted:
                if box_id and description and spreadsheet:
                    final_category = custom_category if custom_category else category
                    new_box = {
                        'BoxID': box_id,
                        'Category': final_category,
                        'Description': description,
                        'Owner': owner,
                        'Status': status,
                        'CreateDate': create_date.strftime('%Y-%m-%d')
                    }
                    
                    if append_box_to_sheet(spreadsheet, new_box):
                        st.session_state.boxes_data.append(new_box)
                        st.session_state.message = {'text': f'成功新增 {box_id}', 'type': 'success'}
                        st.session_state.show_box_form = False
                        st.rerun()
            
            if cancelled:
                st.session_state.show_box_form = False
                st.rerun()
    
    # 篩選資料
    filtered_boxes = st.session_state.boxes_data
    
    if search_boxid:
        filtered_boxes = [b for b in filtered_boxes if search_boxid.lower() in str(b.get('BoxID', '')).lower() or search_boxid.lower() in str(b.get('Description', '')).lower()]
    
    if "全部" not in filter_category:
        filtered_boxes = [b for b in filtered_boxes if b.get('Category') in filter_category]
    
    if "全部" not in filter_owner:
        filtered_boxes = [b for b in filtered_boxes if b.get('Owner') in filter_owner]
    
    if "全部" not in filter_status:
        filtered_boxes = [b for b in filtered_boxes if b.get('Status') in filter_status]
    
    # 顯示表格
    if filtered_boxes:
        df_boxes = pd.DataFrame(filtered_boxes)
        
        # 添加操作列
        st.dataframe(
            df_boxes,
            width="stretch",
            hide_index=True,
            column_config={
                "BoxID": st.column_config.TextColumn("容器/專案編號", width="medium"),
                "Category": st.column_config.TextColumn("類別", width="small"),
                "Description": st.column_config.TextColumn("名稱/敘述", width="large"),
                "Owner": st.column_config.TextColumn("負責人", width="small"),
                "Status": st.column_config.TextColumn("狀態", width="small"),
                "CreateDate": st.column_config.TextColumn("建立日期", width="medium")
            }
        )
        
        # 編輯/刪除功能
        st.subheader("✏️ 編輯/刪除")
        col_edit, col_delete = st.columns(2)
        
        with col_edit:
            box_to_edit = st.selectbox("選擇要編輯的 Box", [""] + [b.get('BoxID', '') for b in filtered_boxes], key="edit_box_select")
            if box_to_edit:
                box_data = next((b for b in filtered_boxes if b.get('BoxID') == box_to_edit), None)
                if box_data:
                    with st.form("edit_box_form"):
                        # 動態建立類別選項
                        category_options = ["一般物料", "專案代碼", "維修件", "電腦主機", "其他"]
                        current_category = box_data.get('Category', '一般物料')
                        if current_category not in category_options:
                            category_options.append(current_category)
                        
                        edit_category = st.selectbox("類別", category_options, 
                                                    index=category_options.index(current_category) if current_category in category_options else 0)
                        edit_description = st.text_input("名稱/敘述", value=box_data.get('Description', ''))
                        edit_owner = st.text_input("負責人", value=box_data.get('Owner', ''))
                        
                        # 動態建立狀態選項
                        status_options = ["使用中", "空閒", "已結案"]
                        current_status = box_data.get('Status', '使用中')
                        if current_status not in status_options:
                            status_options.append(current_status)
                        
                        edit_status = st.selectbox("狀態", status_options,
                                                  index=status_options.index(current_status) if current_status in status_options else 0)
                        
                        if st.form_submit_button("💾 儲存變更", width="stretch"):
                            updated_box = {
                                'BoxID': box_to_edit,
                                'Category': edit_category,
                                'Description': edit_description,
                                'Owner': edit_owner,
                                'Status': edit_status,
                                'CreateDate': box_data.get('CreateDate', '')
                            }
                            
                            if update_box_in_sheet(spreadsheet, box_to_edit, updated_box):
                                idx = next(i for i, b in enumerate(st.session_state.boxes_data) if b.get('BoxID') == box_to_edit)
                                st.session_state.boxes_data[idx] = updated_box
                                st.session_state.message = {'text': f'成功更新 {box_to_edit}', 'type': 'success'}
                                st.rerun()
        
        with col_delete:
            box_to_delete = st.selectbox("選擇要刪除的 Box", [""] + [b.get('BoxID', '') for b in filtered_boxes], key="delete_box_select")
            if box_to_delete:
                st.warning(f"⚠️ 確定要刪除 {box_to_delete}?")
                if st.button("🗑️ 確認刪除", width="stretch", key="confirm_delete_box"):
                    if delete_box_from_sheet(spreadsheet, box_to_delete):
                        st.session_state.boxes_data = [b for b in st.session_state.boxes_data if b.get('BoxID') != box_to_delete]
                        st.session_state.message = {'text': f'成功刪除 {box_to_delete}', 'type': 'success'}
                        st.rerun()
    else:
        st.info("查無資料")

# ==================== Tab 2: 物品清單 ====================
with tab2:
    st.markdown("### 📜 物品明細清單")
    
    # 進階搜尋區域
    with st.expander("🔍 進階搜尋與篩選", expanded=False):
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_item = st.text_input("🔎 物品名稱/序號/規格", key="search_item", placeholder="輸入關鍵字搜尋...")
            boxes = list(set([i.get('BoxID', '') for i in st.session_state.items_data if i.get('BoxID')]))
            filter_box = st.multiselect("📦 所屬 BoxID", ["全部"] + boxes, default=["全部"])
        
        with col2:
            min_qty = st.number_input("📊 庫存數量(最小)", min_value=0, value=0, key="min_qty")
            max_qty = st.number_input("📊 庫存數量(最大)", min_value=0, value=9999, key="max_qty")
        
        with col3:
            locations = list(set([i.get('Location', '') for i in st.session_state.items_data if i.get('Location')]))
            filter_location = st.multiselect("📍 存放位置", ["全部"] + locations, default=["全部"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 操作按鈕區域
    st.markdown('<div class="action-section">', unsafe_allow_html=True)
    col_add, col_import, col_export, col_template = st.columns(4)
    
    with col_add:
        if st.button("➕ 新增物品", width="stretch", key="add_item_btn", type="primary"):
            st.session_state.show_item_form = not st.session_state.get('show_item_form', False)
    
    with col_import:
        uploaded_items = st.file_uploader("📤 批次匯入", type=['csv'], key="import_items", label_visibility="collapsed")
        if uploaded_items:
            try:
                df = pd.read_csv(uploaded_items, encoding='utf-8-sig')
                success_count = 0
                
                st.write("📋 匯入預覽:")
                st.dataframe(df.head(), width="stretch")
                
                if st.button("✅ 確認匯入", key="confirm_import_items"):
                    for _, row in df.iterrows():
                        item_data = {
                            'SN': str(row.get('SN', row.get('序號', row.get('物品序號', '')))),
                            'ItemName': str(row.get('ItemName', row.get('商品名稱', row.get('項目名稱', '')))),
                            'Spec': str(row.get('Spec', row.get('規格型號', ''))),
                            'Location': str(row.get('Location', row.get('存放位置', ''))),
                            'BoxID': str(row.get('BoxID', row.get('所屬編號', ''))),
                            'Quantity': int(row.get('Quantity', row.get('庫存數量', 0))),
                            'UpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        if item_data['SN'] and append_item_to_sheet(spreadsheet, item_data):
                            st.session_state.items_data.append(item_data)
                            success_count += 1
                    st.session_state.message = {'text': f'✅ 成功匯入 {success_count} 筆資料', 'type': 'success'}
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 匯入失敗: {str(e)}")
    
    with col_export:
        if st.session_state.items_data:
            df_export = pd.DataFrame(st.session_state.items_data)
            csv = df_export.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 匯出 CSV",
                data=csv,
                file_name=f"items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch"
            )
    
    with col_template:
        template_data = {
            'SN': ['G0001', 'G0002'],
            'ItemName': ['範例物品1', '範例物品2'],
            'Spec': ['規格A', '規格B'],
            'Location': ['A-01', 'B-02'],
            'BoxID': ['BOX-001', 'BOX-002'],
            'Quantity': [10, 5]
        }
        template_df = pd.DataFrame(template_data)
        template_csv = template_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📄 下載模板",
            data=template_csv,
            file_name="items_template.csv",
            mime="text/csv",
            width="stretch"
        )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 新增表單
    if st.session_state.get('show_item_form', False):
        with st.form("add_item_form"):
            st.subheader("新增物品")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                item_sn = st.text_input("序號 (SN) *", placeholder="SN2024XXX")
                item_name = st.text_input("商品名稱 *", placeholder="輸入名稱")
            
            with col2:
                item_spec = st.text_input("規格型號", placeholder="詳細規格")
                item_location = st.text_input("存放位置", placeholder="A-01")
            
            with col3:
                box_options = [box.get('BoxID', '') for box in st.session_state.boxes_data if box.get('BoxID')]
                item_box = st.selectbox("所屬編號 *", [""] + box_options)
                item_qty = st.number_input("庫存數量", min_value=0, value=1)
            
            col_submit, col_cancel = st.columns([1, 5])
            with col_submit:
                submitted = st.form_submit_button("提交", width="stretch")
            with col_cancel:
                cancelled = st.form_submit_button("取消", width="stretch")
            
            if submitted:
                if item_sn and item_name and item_box and spreadsheet:
                    new_item = {
                        'SN': item_sn,
                        'ItemName': item_name,
                        'Spec': item_spec,
                        'Location': item_location,
                        'BoxID': item_box,
                        'Quantity': item_qty,
                        'UpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    if append_item_to_sheet(spreadsheet, new_item):
                        st.session_state.items_data.append(new_item)
                        st.session_state.message = {'text': f'成功新增物品 {item_name}', 'type': 'success'}
                        st.session_state.show_item_form = False
                        st.rerun()
            
            if cancelled:
                st.session_state.show_item_form = False
                st.rerun()
    
    # 篩選資料
    filtered_items = st.session_state.items_data
    
    if search_item:
        filtered_items = [i for i in filtered_items 
                         if search_item.lower() in str(i.get('ItemName', '')).lower() 
                         or search_item.lower() in str(i.get('SN', '')).lower()
                         or search_item.lower() in str(i.get('Spec', '')).lower()]
    
    if "全部" not in filter_box:
        filtered_items = [i for i in filtered_items if i.get('BoxID') in filter_box]
    
    if "全部" not in filter_location:
        filtered_items = [i for i in filtered_items if i.get('Location') in filter_location]
    
    filtered_items = [i for i in filtered_items if min_qty <= i.get('Quantity', 0) <= max_qty]
    
    # 顯示表格
    if filtered_items:
        df_items = pd.DataFrame(filtered_items)
        st.dataframe(
            df_items,
            width="stretch",
            hide_index=True,
            column_config={
                "SN": st.column_config.TextColumn("序號", width="medium"),
                "ItemName": st.column_config.TextColumn("商品名稱", width="medium"),
                "Spec": st.column_config.TextColumn("規格型號", width="medium"),
                "Location": st.column_config.TextColumn("存放位置", width="small"),
                "BoxID": st.column_config.TextColumn("所屬編號", width="medium"),
                "Quantity": st.column_config.NumberColumn("庫存數量", width="small"),
                "UpdateTime": st.column_config.TextColumn("更新時間", width="medium")
            }
        )
        
        # 編輯/刪除功能
        st.subheader("✏️ 編輯/刪除")
        col_edit, col_delete = st.columns(2)
        
        with col_edit:
            item_to_edit = st.selectbox("選擇要編輯的物品", [""] + [f"{i.get('SN', '')} - {i.get('ItemName', '')}" for i in filtered_items], key="edit_item_select")
            if item_to_edit:
                edit_sn = item_to_edit.split(" - ")[0]
                item_data = next((i for i in filtered_items if i.get('SN') == edit_sn), None)
                if item_data:
                    with st.form("edit_item_form"):
                        edit_name = st.text_input("商品名稱", value=item_data.get('ItemName', ''))
                        edit_spec = st.text_input("規格型號", value=item_data.get('Spec', ''))
                        edit_location = st.text_input("存放位置", value=item_data.get('Location', ''))
                        box_options = [box.get('BoxID', '') for box in st.session_state.boxes_data if box.get('BoxID')]
                        edit_box = st.selectbox("所屬編號", box_options, index=box_options.index(item_data.get('BoxID', box_options[0])) if item_data.get('BoxID') in box_options else 0)
                        edit_qty = st.number_input("庫存數量", min_value=0, value=item_data.get('Quantity', 0))
                        
                        if st.form_submit_button("💾 儲存變更", width="stretch"):
                            updated_item = {
                                'SN': edit_sn,
                                'ItemName': edit_name,
                                'Spec': edit_spec,
                                'Location': edit_location,
                                'BoxID': edit_box,
                                'Quantity': edit_qty,
                                'UpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            if update_item_in_sheet(spreadsheet, edit_sn, updated_item):
                                idx = next(i for i, item in enumerate(st.session_state.items_data) if item.get('SN') == edit_sn)
                                st.session_state.items_data[idx] = updated_item
                                st.session_state.message = {'text': f'成功更新 {edit_sn}', 'type': 'success'}
                                st.rerun()
        
        with col_delete:
            item_to_delete = st.selectbox("選擇要刪除的物品", [""] + [f"{i.get('SN', '')} - {i.get('ItemName', '')}" for i in filtered_items], key="delete_item_select")
            if item_to_delete:
                delete_sn = item_to_delete.split(" - ")[0]
                st.warning(f"⚠️ 確定要刪除 {item_to_delete}?")
                if st.button("🗑️ 確認刪除", width="stretch", key="confirm_delete_item"):
                    if delete_item_from_sheet(spreadsheet, delete_sn):
                        st.session_state.items_data = [i for i in st.session_state.items_data if i.get('SN') != delete_sn]
                        st.session_state.message = {'text': f'成功刪除 {delete_sn}', 'type': 'success'}
                        st.rerun()
    else:
        st.info("查無資料")

# ==================== Tab 3: 交易紀錄 (整合調撥功能) ====================
with tab3:
    st.header("📝 交易/異動紀錄")
    
    # 建立子標籤
    trans_tab1, trans_tab2, trans_tab3 = st.tabs([
        "📝 一般交易", 
        "🔄 容器間調撥",
        "📊 交易記錄查詢"
    ])
    
    # ========== 子標籤 1: 一般交易 (入庫/出庫/報廢) ==========
    with trans_tab1:
        with st.form("transaction_form"):
            st.subheader("執行新交易")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                item_options = [f"{item.get('SN', '')} - {item.get('ItemName', '')}" 
                              for item in st.session_state.items_data 
                              if item.get('SN') and item.get('ItemName')]
                trans_item = st.selectbox("選擇物品 (SN) *", [""] + item_options, key="simple_trans_item")
                trans_action = st.selectbox("異動類型 *", ["入庫", "出庫", "報廢"], key="simple_trans_action")
            
            with col2:
                trans_qty = st.number_input("異動數量 *", min_value=1, value=1, key="simple_trans_qty")
                trans_operator = st.text_input("操作人員", placeholder="姓名", key="simple_trans_operator")
            
            with col3:
                trans_remark = st.text_area("備註", placeholder="異動原因說明", height=100, key="simple_trans_remark")
            
            submitted = st.form_submit_button("執行交易", use_container_width=True, type="primary")
            
            if submitted:
                if trans_item and spreadsheet:
                    trans_sn = trans_item.split(" - ")[0]
                    
                    item_idx = next((i for i, item in enumerate(st.session_state.items_data) 
                                   if item.get('SN') == trans_sn), None)
                    
                    if item_idx is not None:
                        item = st.session_state.items_data[item_idx]
                        current_qty = item.get('Quantity', 0)
                        
                        if trans_action == '入庫':
                            qty_change = trans_qty
                            new_qty = current_qty + trans_qty
                        elif trans_action in ['出庫', '報廢']:
                            if current_qty < trans_qty:
                                st.session_state.message = {'text': f'庫存不足 (當前: {current_qty}, 需要: {trans_qty})', 'type': 'error'}
                                st.rerun()
                            qty_change = -trans_qty
                            new_qty = current_qty - trans_qty
                        else:
                            qty_change = trans_qty
                            new_qty = current_qty
                        
                        update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        new_transaction = {
                            'LogID': st.session_state.next_log_id,
                            'BoxID': item.get('BoxID', ''),
                            'SN': trans_sn,
                            'ActionType': trans_action,
                            'TransQty': qty_change,
                            'Operator': trans_operator or '系統',
                            'Remark': trans_remark or '',
                            'Timestamp': update_time
                        }
                        
                        if append_transaction_to_sheet(spreadsheet, new_transaction):
                            if update_item_quantity(spreadsheet, trans_sn, new_qty, update_time):
                                st.session_state.items_data[item_idx]['Quantity'] = new_qty
                                st.session_state.items_data[item_idx]['UpdateTime'] = update_time
                                st.session_state.transactions_data.insert(0, new_transaction)
                                st.session_state.next_log_id += 1
                                
                                st.session_state.message = {
                                    'text': f'✅ 交易成功: {trans_action} {trans_qty} 件，當前庫存: {new_qty}',
                                    'type': 'success'
                                }
                                st.rerun()
    
    # ========== 子標籤 2: 容器間調撥 (Box to Box) ==========
    with trans_tab2:
        st.markdown('<div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border: 2px solid #3b82f6;">', unsafe_allow_html=True)
        st.subheader("📦 容器間調撥 (Box → Box)")
        st.caption("在不同容器(Box)之間調撥物品")
        
        with st.form("box_transfer_form"):
            # ===== 步驟 1: 選擇來源容器 =====
            st.markdown("### 📤 步驟 1: 選擇來源容器")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 取得所有 Box 選項
                box_options = [
                    f"{box.get('BoxID', '')} - {box.get('Description', '')} ({box.get('Category', '')})"
                    for box in st.session_state.boxes_data
                    if box.get('BoxID')
                ]
                
                source_box = st.selectbox(
                    "📦 來源容器 *",
                    [""] + box_options,
                    key="box_transfer_source_box",
                    help="選擇要調出物品的容器"
                )
            
            with col2:
                # 根據選擇的來源容器,顯示該容器內的物品
                if source_box:
                    source_box_id = source_box.split(" - ")[0]
                    
                    # 篩選該容器內的物品
                    items_in_box = [
                        item for item in st.session_state.items_data
                        if item.get('BoxID') == source_box_id and item.get('Quantity', 0) > 0
                    ]
                    
                    if items_in_box:
                        st.success(f"📊 容器內有 {len(items_in_box)} 種物品")
                        
                        # 顯示容器內物品摘要
                        with st.expander("查看容器內物品", expanded=False):
                            for item in items_in_box[:5]:  # 只顯示前5個
                                st.caption(
                                    f"• {item.get('ItemName', '')} "
                                    f"(SN: {item.get('SN', '')}, "
                                    f"庫存: {item.get('Quantity', 0)})"
                                )
                            if len(items_in_box) > 5:
                                st.caption(f"... 還有 {len(items_in_box) - 5} 項")
                    else:
                        st.warning("⚠️ 此容器內沒有物品或物品庫存為 0")
            
            st.divider()
            
            # ===== 步驟 2: 選擇要調撥的物品 =====
            st.markdown("### 📦 步驟 2: 選擇要調撥的物品")
            
            if source_box:
                source_box_id = source_box.split(" - ")[0]
                items_in_box = [
                    item for item in st.session_state.items_data
                    if item.get('BoxID') == source_box_id and item.get('Quantity', 0) > 0
                ]
                
                if items_in_box:
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        # 物品選項
                        item_options = [
                            f"{item.get('SN', '')} - {item.get('ItemName', '')} (庫存: {item.get('Quantity', 0)})"
                            for item in items_in_box
                        ]
                        
                        selected_item = st.selectbox(
                            "選擇物品 *",
                            [""] + item_options,
                            key="box_transfer_item",
                            help="選擇要調撥的物品"
                        )
                    
                    with col4:
                        # 調撥數量
                        max_qty = 1
                        if selected_item:
                            selected_sn = selected_item.split(" - ")[0]
                            selected_data = next(
                                (i for i in items_in_box if i.get('SN') == selected_sn),
                                None
                            )
                            if selected_data:
                                max_qty = selected_data.get('Quantity', 1)
                        
                        transfer_qty = st.number_input(
                            "調撥數量 *",
                            min_value=1,
                            max_value=max_qty,
                            value=min(1, max_qty),
                            key="box_transfer_qty",
                            help=f"最多可調撥 {max_qty} 件"
                        )
                        
                        # 顯示調撥後庫存預覽
                        if selected_item:
                            remaining = max_qty - transfer_qty
                            st.info(f"📊 調撥後來源庫存: {remaining} 件")
                else:
                    st.warning("⚠️ 請先選擇有物品的來源容器")
                    selected_item = None
            else:
                st.info("ℹ️ 請先選擇來源容器")
                selected_item = None
            
            st.divider()
            
            # ===== 步驟 3: 選擇目標容器 =====
            st.markdown("### 📥 步驟 3: 選擇目標容器")
            
            col5, col6 = st.columns(2)
            
            with col5:
                # 目標容器選項 (排除來源容器)
                target_box_options = [
                    f"{box.get('BoxID', '')} - {box.get('Description', '')} ({box.get('Category', '')})"
                    for box in st.session_state.boxes_data
                    if box.get('BoxID') and (not source_box or box.get('BoxID') != source_box.split(" - ")[0])
                ]
                
                target_box = st.selectbox(
                    "📦 目標容器 *",
                    [""] + target_box_options,
                    key="box_transfer_target_box",
                    help="選擇要調入物品的容器"
                )
            
            with col6:
                # 目標位置
                target_location = st.text_input(
                    "📍 目標位置 (選填)",
                    placeholder="例如: A-01, B-02",
                    key="box_transfer_location",
                    help="在目標容器內的具體位置"
                )
                
                # 顯示目標容器資訊
                if target_box:
                    target_box_id = target_box.split(" - ")[0]
                    target_box_data = next(
                        (b for b in st.session_state.boxes_data 
                         if b.get('BoxID') == target_box_id),
                        None
                    )
                    if target_box_data:
                        st.caption(f"負責人: {target_box_data.get('Owner', '未設定')}")
                        st.caption(f"狀態: {target_box_data.get('Status', '未設定')}")
            
            st.divider()
            
            # ===== 步驟 4: 其他資訊 =====
            st.markdown("### 📝 步驟 4: 填寫其他資訊")
            
            col7, col8 = st.columns(2)
            
            with col7:
                operator = st.text_input(
                    "👤 操作人員",
                    placeholder="姓名",
                    key="box_transfer_operator"
                )
            
            with col8:
                remark = st.text_area(
                    "📝 備註",
                    placeholder="調撥原因說明",
                    height=80,
                    key="box_transfer_remark"
                )
            
            # ===== 提交按鈕 =====
            col_submit, col_cancel = st.columns([1, 5])
            
            with col_submit:
                submitted = st.form_submit_button(
                    "📥 執行調撥",
                    type="primary",
                    use_container_width=True
                )
            
            with col_cancel:
                cancelled = st.form_submit_button(
                    "取消",
                    use_container_width=True
                )
            
            # ===== 處理表單提交 =====
            if submitted:
                # 驗證
                if not source_box:
                    st.error("❌ 請選擇來源容器")
                elif not selected_item:
                    st.error("❌ 請選擇要調撥的物品")
                elif not target_box:
                    st.error("❌ 請選擇目標容器")
                else:
                    # 執行調撥邏輯
                    source_sn = selected_item.split(" - ")[0]
                    target_box_id = target_box.split(" - ")[0]
                    
                    # 找到來源物品
                    source_item_data = next(
                        (i for i in st.session_state.items_data if i.get('SN') == source_sn),
                        None
                    )
                    
                    if source_item_data:
                        source_qty = source_item_data.get('Quantity', 0)
                        
                        if source_qty < transfer_qty:
                            st.error(f"❌ 庫存不足 (當前: {source_qty}, 需要: {transfer_qty})")
                        else:
                            # 執行調撥
                            update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            new_source_qty = source_qty - transfer_qty
                            
                            # 建立新物品記錄 (在目標容器)
                            new_item_sn = f"{source_sn}-T{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            new_item = {
                                'SN': new_item_sn,
                                'ItemName': source_item_data.get('ItemName', ''),
                                'Spec': source_item_data.get('Spec', ''),
                                'Location': target_location or '',
                                'BoxID': target_box_id,
                                'Quantity': transfer_qty,
                                'UpdateTime': update_time
                            }
                            
                            # 記錄 1: 調撥出庫
                            trans_out = {
                                'LogID': st.session_state.next_log_id,
                                'BoxID': source_item_data.get('BoxID', ''),
                                'SN': source_sn,
                                'ActionType': '調撥出庫',
                                'TransQty': -transfer_qty,
                                'Operator': operator or '系統',
                                'Remark': f"調撥至 {target_box_id} | {remark or ''}",
                                'Timestamp': update_time
                            }
                            
                            # 記錄 2: 調撥入庫
                            trans_in = {
                                'LogID': st.session_state.next_log_id + 1,
                                'BoxID': target_box_id,
                                'SN': new_item_sn,
                                'ActionType': '調撥入庫',
                                'TransQty': transfer_qty,
                                'Operator': operator or '系統',
                                'Remark': f"來自 {source_item_data.get('BoxID', '')} ({source_sn}) | {remark or ''}",
                                'Timestamp': update_time
                            }
                            
                            # 寫入資料庫
                            if (append_item_to_sheet(spreadsheet, new_item) and
                                append_transaction_to_sheet(spreadsheet, trans_out) and
                                append_transaction_to_sheet(spreadsheet, trans_in) and
                                update_item_quantity(spreadsheet, source_sn, new_source_qty, update_time)):
                                
                                # 更新本地資料
                                source_idx = next(
                                    i for i, item in enumerate(st.session_state.items_data) 
                                    if item.get('SN') == source_sn
                                )
                                st.session_state.items_data[source_idx]['Quantity'] = new_source_qty
                                st.session_state.items_data[source_idx]['UpdateTime'] = update_time
                                st.session_state.items_data.append(new_item)
                                
                                st.session_state.transactions_data.insert(0, trans_in)
                                st.session_state.transactions_data.insert(0, trans_out)
                                st.session_state.next_log_id += 2
                                
                                success_msg = f'''✅ 調撥成功:

📤 來源: {source_sn} ({source_item_data.get('BoxID', '')})
   數量: {source_qty} → {new_source_qty} (-{transfer_qty})

📥 目標: {new_item_sn} ({target_box_id})
   數量: 0 → {transfer_qty} (+{transfer_qty})
'''
                                st.session_state.message = {'text': success_msg, 'type': 'success'}
                                st.rerun()
            
            if cancelled:
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== 子標籤 3: 交易記錄查詢 ==========
    with trans_tab3:
        # 進階搜尋區域
        with st.expander("🔍 進階搜尋與篩選", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                action_types = list(set([t.get('ActionType', '') for t in st.session_state.transactions_data if t.get('ActionType')]))
                filter_action = st.multiselect("異動類型", ["全部"] + action_types, default=["全部"])
            
            with col2:
                start_date = st.date_input("開始日期", value=datetime.now() - timedelta(days=30))
                end_date = st.date_input("結束日期", value=datetime.now())
            
            with col3:
                operators = list(set([t.get('Operator', '') for t in st.session_state.transactions_data if t.get('Operator')]))
                filter_operator = st.multiselect("操作人員", ["全部"] + operators, default=["全部"])
        
        # 篩選資料
        filtered_trans = st.session_state.transactions_data
        
        if "全部" not in filter_action:
            filtered_trans = [t for t in filtered_trans if t.get('ActionType') in filter_action]
        
        if "全部" not in filter_operator:
            filtered_trans = [t for t in filtered_trans if t.get('Operator') in filter_operator]
        
        # 日期篩選
        filtered_trans = [t for t in filtered_trans 
                         if t.get('Timestamp') and 
                         start_date.strftime('%Y-%m-%d') <= t.get('Timestamp', '')[:10] <= end_date.strftime('%Y-%m-%d')]
        
        # 顯示表格
        if filtered_trans:
            df_trans = pd.DataFrame(filtered_trans)
            st.dataframe(
                df_trans,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "LogID": st.column_config.NumberColumn("紀錄編號", width="small"),
                    "BoxID": st.column_config.TextColumn("所屬編號", width="medium"),
                    "SN": st.column_config.TextColumn("物品序號", width="medium"),
                    "ActionType": st.column_config.TextColumn("異動類型", width="small"),
                    "TransQty": st.column_config.NumberColumn("異動數量", width="small"),
                    "Operator": st.column_config.TextColumn("操作人員", width="small"),
                    "Remark": st.column_config.TextColumn("備註", width="large"),
                    "Timestamp": st.column_config.TextColumn("交易時間", width="medium")
                }
            )
        else:
            st.info("查無交易記錄")