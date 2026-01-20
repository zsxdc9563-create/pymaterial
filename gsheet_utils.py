# gsheet_utils.py
"""
Google Sheets 連線與資料操作工具
"""
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from config import SCOPES, SPREADSHEET_ID, SHEET_NAMES, FIELD_MAPPING


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
            # 數字類型欄位的處理
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                try:
                    normalized[standard_name] = int(value) if value != '' else 0
                except (ValueError, TypeError):
                    normalized[standard_name] = 0
            else:
                normalized[standard_name] = str(value) if value else ''
        else:
            # 如果欄位不存在，設置默認值
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                normalized[standard_name] = 0
            else:
                normalized[standard_name] = ''
    return normalized


def load_sheet_data(spreadsheet, sheet_name, data_type):
    """通用的 Sheet 資料讀取函數"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        
        # 儲存除錯資訊
        st.session_state[f'debug_{data_type}_raw'] = data[:3] if data else []
        st.session_state[f'debug_{data_type}_headers'] = worksheet.row_values(1)
        
        if not data:
            return []
        
        normalized_data = [normalize_row(row, FIELD_MAPPING[data_type]) for row in data]
        
        # 根據資料類型過濾空行
        if data_type == 'boxes':
            return [row for row in normalized_data if row.get('BoxID')]
        elif data_type == 'items':
            return [row for row in normalized_data if row.get('SN')]
        elif data_type == 'transactions':
            return [row for row in normalized_data if row.get('LogID') or row.get('SN')]
        
        return normalized_data
    except Exception as e:
        st.error(f"讀取 {sheet_name} 時發生問題: {str(e)}")
        return []


def append_to_sheet(spreadsheet, sheet_name, data_dict, data_type):
    """通用的 Sheet 資料寫入函數"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        
        # 根據實際標題列順序建立資料行
        row = []
        for header in headers:
            # 找到對應的標準欄位名
            for std_name, possible_names in FIELD_MAPPING[data_type].items():
                if header in possible_names:
                    row.append(data_dict.get(std_name, ''))
                    break
            else:
                row.append('')
        
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入 {sheet_name} 失敗: {str(e)}")
        return False


def update_item_quantity(spreadsheet, sn, new_quantity, update_time):
    """更新物品庫存數量"""
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES['items'])
        headers = worksheet.row_values(1)
        
        # 找到欄位索引
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
        
        # 找到對應的 SN 行
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


def get_next_log_id(transactions_data):
    """計算下一個 LogID，修正空列表錯誤"""
    if not transactions_data:
        return 1
    
    valid_log_ids = [t.get('LogID', 0) for t in transactions_data if t.get('LogID')]
    
    if not valid_log_ids:
        return 1
    
    return max(valid_log_ids) + 1