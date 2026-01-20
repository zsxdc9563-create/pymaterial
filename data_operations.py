# data_operations.py
"""
資料操作與業務邏輯
"""
import streamlit as st
from datetime import datetime
from gsheet_utils import (
    append_to_sheet, 
    update_item_quantity, 
    load_sheet_data,
    update_row_in_sheet,
    delete_row_from_sheet
)
from config import SHEET_NAMES, FIELD_MAPPING


# ==================== 資料載入函數 (加強版,包含除錯資訊) ====================

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
            # 數字類型欄位
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                try:
                    normalized[standard_name] = int(value) if value != '' else 0
                except (ValueError, TypeError):
                    normalized[standard_name] = 0
            else:
                normalized[standard_name] = str(value) if value else ''
        else:
            # 欄位不存在時的預設值
            if standard_name in ['Quantity', 'TransQty', 'LogID']:
                normalized[standard_name] = 0
            else:
                normalized[standard_name] = ''
    return normalized


def load_boxes_from_sheet(spreadsheet):
    """從 Sheet 讀取物料總覽 (加強版,包含除錯)"""
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES['boxes'])
        data = worksheet.get_all_records()
        
        # 儲存除錯資訊
        st.session_state.debug_boxes_raw = data[:3] if data else []
        st.session_state.debug_boxes_headers = worksheet.row_values(1)
        
        if not data:
            st.session_state.debug_boxes_normalized = []
            return []
        
        # 標準化資料
        normalized_data = [normalize_row(row, FIELD_MAPPING['boxes']) for row in data]
        
        # 過濾條件:只要有 BoxID 或任何欄位有值就保留
        result = [row for row in normalized_data if row.get('BoxID') or any(row.values())]
        
        # 儲存標準化後的除錯資訊
        st.session_state.debug_boxes_normalized = result[:3] if result else []
        
        return result
    except Exception as e:
        st.error(f"讀取物料總覽時發生問題: {str(e)}")
        st.exception(e)  # 顯示完整錯誤堆疊
        return []


def load_items_from_sheet(spreadsheet):
    """從 Sheet 讀取物品清單"""
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES['items'])
        data = worksheet.get_all_records()
        
        # 儲存除錯資訊
        st.session_state.debug_items_raw = data[:3] if data else []
        st.session_state.debug_items_headers = worksheet.row_values(1)
        
        if not data:
            return []
        
        # 標準化資料
        normalized_data = [normalize_row(row, FIELD_MAPPING['items']) for row in data]
        result = [row for row in normalized_data if row.get('SN')]
        
        return result
    except Exception as e:
        st.error(f"讀取物品清單時發生問題: {str(e)}")
        st.exception(e)
        return []


def load_transactions_from_sheet(spreadsheet):
    """從 Sheet 讀取交易記錄 (加強版,包含除錯)"""
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES['transactions'])
        data = worksheet.get_all_records()
        
        # 儲存除錯資訊
        st.session_state.debug_trans_raw = data[:3] if data else []
        st.session_state.debug_trans_headers = worksheet.row_values(1)
        
        if not data:
            st.session_state.debug_trans_normalized = []
            return []
        
        # 標準化資料
        normalized_data = [normalize_row(row, FIELD_MAPPING['transactions']) for row in data]
        
        # 過濾條件:只要有 LogID、SN 或任何欄位有值就保留
        result = [row for row in normalized_data 
                 if row.get('LogID') or row.get('SN') or any(row.values())]
        
        # 儲存標準化後的除錯資訊
        st.session_state.debug_trans_normalized = result[:3] if result else []
        
        return result
    except Exception as e:
        st.error(f"讀取交易記錄時發生問題: {str(e)}")
        st.exception(e)
        return []


# ==================== 業務邏輯函數 (你原本的) ====================

def add_new_box(spreadsheet, box_data):
    """新增 Box 到資料庫"""
    if append_to_sheet(spreadsheet, SHEET_NAMES['boxes'], box_data, 'boxes'):
        st.session_state.boxes_data.append(box_data)
        return True
    return False


def add_new_item(spreadsheet, item_data):
    """新增物品到資料庫"""
    if append_to_sheet(spreadsheet, SHEET_NAMES['items'], item_data, 'items'):
        st.session_state.items_data.append(item_data)
        return True
    return False


def execute_transaction(spreadsheet, trans_sn, trans_action, trans_qty, trans_operator, trans_remark, 
                       target_sn=None, target_box=None, target_location=None):
    """
    執行交易操作
    
    參數:
        trans_sn: 來源物品序號
        trans_action: 交易類型 (入庫/出庫/報廢/調撥出庫/調撥入庫)
        trans_qty: 數量
        trans_operator: 操作人員
        trans_remark: 備註
        target_sn: 目標物品序號 (調撥時使用)
        target_box: 目標容器 (調撥時使用)
        target_location: 目標位置 (調撥時使用)
    """
    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ========== 調撥入庫邏輯 ==========
    if trans_action == '調撥入庫':
        return _execute_transfer_in(
            spreadsheet, trans_sn, trans_qty, trans_operator, trans_remark,
            target_sn, target_box, target_location, update_time
        )
    
    # ========== 一般交易邏輯 ==========
    # 找到對應物品
    item_idx = next((i for i, item in enumerate(st.session_state.items_data) 
                   if item.get('SN') == trans_sn), None)
    
    if item_idx is None:
        return False, "找不到對應物品"
    
    item = st.session_state.items_data[item_idx]
    current_qty = item.get('Quantity', 0)
    
    # 計算異動數量
    if trans_action == '入庫':
        qty_change = trans_qty
        new_qty = current_qty + trans_qty
    elif trans_action in ['出庫', '報廢', '調撥出庫']:
        if current_qty < trans_qty:
            return False, f"庫存不足,無法執行 (當前庫存: {current_qty})"
        qty_change = -trans_qty
        new_qty = current_qty - trans_qty
    else:
        return False, f"不支援的交易類型: {trans_action}"
    
    # 建立交易記錄
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
    
    # 寫入交易記錄
    if not append_to_sheet(spreadsheet, SHEET_NAMES['transactions'], new_transaction, 'transactions'):
        return False, "寫入交易記錄失敗"
    
    # 更新庫存
    if not update_item_quantity(spreadsheet, trans_sn, new_qty, update_time):
        return False, "更新庫存失敗"
    
    # 更新本地資料
    st.session_state.items_data[item_idx]['Quantity'] = new_qty
    st.session_state.items_data[item_idx]['UpdateTime'] = update_time
    st.session_state.transactions_data.insert(0, new_transaction)
    st.session_state.next_log_id += 1
    
    success_msg = f'交易成功: {trans_action} {trans_qty} 件，當前庫存: {new_qty}'
    return True, success_msg


def _execute_transfer_in(spreadsheet, source_sn, trans_qty, trans_operator, trans_remark,
                         target_sn, target_box, target_location, update_time):
    """
    執行調撥入庫 (內部函數)
    
    流程:
    1. 檢查來源物品庫存是否足夠
    2. 來源物品扣除庫存 (調撥出庫)
    3. 目標物品增加庫存 (調撥入庫)
    4. 記錄兩筆交易記錄
    """
    
    # ===== 步驟 1: 檢查來源物品 =====
    source_idx = next((i for i, item in enumerate(st.session_state.items_data) 
                      if item.get('SN') == source_sn), None)
    
    if source_idx is None:
        return False, "找不到來源物品"
    
    source_item = st.session_state.items_data[source_idx]
    source_qty = source_item.get('Quantity', 0)
    
    if source_qty < trans_qty:
        return False, f"來源庫存不足 (當前: {source_qty}, 需要: {trans_qty})"
    
    # ===== 步驟 2: 檢查目標物品 (如果提供 target_sn) =====
    target_idx = None
    target_item = None
    target_qty = 0
    
    if target_sn:
        # 目標是既有物品,增加其庫存
        target_idx = next((i for i, item in enumerate(st.session_state.items_data) 
                          if item.get('SN') == target_sn), None)
        
        if target_idx is None:
            return False, f"找不到目標物品: {target_sn}"
        
        target_item = st.session_state.items_data[target_idx]
        target_qty = target_item.get('Quantity', 0)
    else:
        # 目標是新建物品 (需要 target_box 和其他資訊)
        if not target_box:
            return False, "調撥到新位置時必須指定目標容器"
        
        # 建立新物品記錄
        new_item_sn = f"{source_sn}-T{datetime.now().strftime('%Y%m%d%H%M%S')}"
        target_item = {
            'SN': new_item_sn,
            'ItemName': source_item.get('ItemName', ''),
            'Spec': source_item.get('Spec', ''),
            'Location': target_location or '',
            'BoxID': target_box,
            'Quantity': 0,
            'UpdateTime': update_time
        }
        
        # 新增到資料庫
        if not append_to_sheet(spreadsheet, SHEET_NAMES['items'], target_item, 'items'):
            return False, "建立目標物品記錄失敗"
        
        st.session_state.items_data.append(target_item)
        target_idx = len(st.session_state.items_data) - 1
        target_sn = new_item_sn
    
    # ===== 步驟 3: 執行調撥 =====
    new_source_qty = source_qty - trans_qty
    new_target_qty = target_qty + trans_qty
    
    # 記錄 1: 來源物品調撥出庫
    trans_out = {
        'LogID': st.session_state.next_log_id,
        'BoxID': source_item.get('BoxID', ''),
        'SN': source_sn,
        'ActionType': '調撥出庫',
        'TransQty': -trans_qty,
        'Operator': trans_operator or '系統',
        'Remark': f"調撥至 {target_box or target_sn} | {trans_remark or ''}",
        'Timestamp': update_time
    }
    
    # 記錄 2: 目標物品調撥入庫
    trans_in = {
        'LogID': st.session_state.next_log_id + 1,
        'BoxID': target_box or target_item.get('BoxID', ''),
        'SN': target_sn,
        'ActionType': '調撥入庫',
        'TransQty': trans_qty,
        'Operator': trans_operator or '系統',
        'Remark': f"來自 {source_item.get('BoxID', '')} ({source_sn}) | {trans_remark or ''}",
        'Timestamp': update_time
    }
    
    # ===== 步驟 4: 寫入資料庫 =====
    # 寫入交易記錄
    if not append_to_sheet(spreadsheet, SHEET_NAMES['transactions'], trans_out, 'transactions'):
        return False, "寫入來源交易記錄失敗"
    
    if not append_to_sheet(spreadsheet, SHEET_NAMES['transactions'], trans_in, 'transactions'):
        return False, "寫入目標交易記錄失敗"
    
    # 更新來源庫存
    if not update_item_quantity(spreadsheet, source_sn, new_source_qty, update_time):
        return False, "更新來源庫存失敗"
    
    # 更新目標庫存
    if not update_item_quantity(spreadsheet, target_sn, new_target_qty, update_time):
        return False, "更新目標庫存失敗"
    
    # ===== 步驟 5: 更新本地資料 =====
    st.session_state.items_data[source_idx]['Quantity'] = new_source_qty
    st.session_state.items_data[source_idx]['UpdateTime'] = update_time
    
    st.session_state.items_data[target_idx]['Quantity'] = new_target_qty
    st.session_state.items_data[target_idx]['UpdateTime'] = update_time
    
    st.session_state.transactions_data.insert(0, trans_in)
    st.session_state.transactions_data.insert(0, trans_out)
    st.session_state.next_log_id += 2
    
    success_msg = f'''✅ 調撥成功:
    
📤 來源: {source_sn} ({source_item.get('BoxID', '')})
   數量: {source_qty} → {new_source_qty} (-{trans_qty})
    
📥 目標: {target_sn} ({target_box or target_item.get('BoxID', '')})
   數量: {target_qty} → {new_target_qty} (+{trans_qty})
'''
    
    return True, success_msg


def update_box(spreadsheet, box_id, updated_data):
    """更新 Box 資料"""
    try:
        if update_row_in_sheet(spreadsheet, SHEET_NAMES['boxes'], box_id, updated_data, 'boxes'):
            # 更新本地資料
            idx = next(i for i, b in enumerate(st.session_state.boxes_data) 
                      if b.get('BoxID') == box_id)
            st.session_state.boxes_data[idx] = updated_data
            return True
        return False
    except Exception as e:
        st.error(f"更新 Box 失敗: {str(e)}")
        return False


def update_item(spreadsheet, sn, updated_data):
    """更新物品資料"""
    try:
        if update_row_in_sheet(spreadsheet, SHEET_NAMES['items'], sn, updated_data, 'items'):
            # 更新本地資料
            idx = next(i for i, item in enumerate(st.session_state.items_data) 
                      if item.get('SN') == sn)
            st.session_state.items_data[idx] = updated_data
            return True
        return False
    except Exception as e:
        st.error(f"更新物品失敗: {str(e)}")
        return False


def delete_box(spreadsheet, box_id):
    """刪除 Box"""
    try:
        if delete_row_from_sheet(spreadsheet, SHEET_NAMES['boxes'], box_id, 'boxes'):
            # 更新本地資料
            st.session_state.boxes_data = [
                b for b in st.session_state.boxes_data if b.get('BoxID') != box_id
            ]
            return True
        return False
    except Exception as e:
        st.error(f"刪除 Box 失敗: {str(e)}")
        return False


def delete_item(spreadsheet, sn):
    """刪除物品"""
    try:
        if delete_row_from_sheet(spreadsheet, SHEET_NAMES['items'], sn, 'items'):
            # 更新本地資料
            st.session_state.items_data = [
                i for i in st.session_state.items_data if i.get('SN') != sn
            ]
            return True
        return False
    except Exception as e:
        st.error(f"刪除物品失敗: {str(e)}")
        return False


# ==================== 工具函數 (你原本的) ====================

def filter_items(items_list, search_query):
    """過濾物品列表"""
    if not search_query:
        return items_list
    
    return [
        item for item in items_list
        if search_query.lower() in str(item.get('ItemName', '')).lower() or
           search_query.lower() in str(item.get('BoxID', '')).lower() or
           search_query.lower() in str(item.get('SN', '')).lower()
    ]


def get_item_options():
    """獲取物品選項列表"""
    return [f"{item.get('SN', '')} - {item.get('ItemName', '')}" 
            for item in st.session_state.items_data 
            if item.get('SN') and item.get('ItemName')]


def get_box_options():
    """獲取 Box 選項列表"""
    return [box.get('BoxID', '') for box in st.session_state.boxes_data if box.get('BoxID')]


# ==================== 診斷工具函數 (新增) ====================

def get_field_mapping_status(sheet_type):
    """取得欄位映射狀態 (用於除錯)"""
    headers_key = f'debug_{sheet_type}_headers'
    if not hasattr(st.session_state, headers_key):
        return None
    
    headers = getattr(st.session_state, headers_key)
    if not headers:
        return None
    
    mapping_result = {}
    for std_name, possible_names in FIELD_MAPPING[sheet_type].items():
        found = None
        for name in possible_names:
            if name in headers:
                found = name
                break
        mapping_result[std_name] = found or "❌ 未找到"
    
    return mapping_result