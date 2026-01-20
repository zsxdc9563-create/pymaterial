# ui_components.py
"""
可重用的 UI 元件
包含樣式、訊息顯示、除錯工具、統計資訊、調撥表單等
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import FIELD_MAPPING, UI_OPTIONS, ICONS, COLOR_THEME


# ==================== 樣式相關 ====================

def apply_custom_css():
    """應用自定義 CSS 樣式 (優化版)"""
    st.markdown(f"""
    <style>
        /* 主標題區塊 */
        .main-header {{
            background: linear-gradient(135deg, {COLOR_THEME['primary']} 0%, {COLOR_THEME['secondary']} 100%);
            padding: 2.5rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        /* 訊息樣式 */
        .success-msg {{
            padding: 1rem;
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            color: #065f46;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid {COLOR_THEME['success']};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .error-msg {{
            padding: 1rem;
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid {COLOR_THEME['error']};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .warning-msg {{
            padding: 1rem;
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid {COLOR_THEME['warning']};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .info-box {{
            padding: 1rem;
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            color: #1e40af;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid {COLOR_THEME['info']};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        /* 除錯區塊 */
        .debug-box {{
            padding: 1.5rem;
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
            border-radius: 12px;
            margin: 1rem 0;
            border: 2px solid {COLOR_THEME['warning']};
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        /* 篩選區域 */
        .filter-section {{
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }}
        
        /* 操作區域 */
        .action-section {{
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        /* 調撥區塊樣式 */
        .transfer-section {{
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border: 2px solid {COLOR_THEME['info']};
        }}
        
        /* 按鈕樣式優化 */
        .stButton > button {{
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }}
        
        /* 標題樣式 */
        h1, h2, h3 {{
            font-weight: 600;
        }}
        
        /* 指標卡片 */
        .metric-card {{
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin: 0.5rem 0;
        }}
    </style>
    """, unsafe_allow_html=True)


# ==================== 訊息顯示 ====================

def display_message():
    """顯示系統訊息 (支援多種類型)"""
    if 'message' not in st.session_state or not st.session_state.message:
        return
    
    msg = st.session_state.message
    msg_type = msg.get('type', 'info')
    msg_text = msg.get('text', '')
    
    icon_map = {
        'success': ICONS['success'],
        'error': ICONS['error'],
        'warning': ICONS['warning'],
        'info': ICONS['info']
    }
    
    icon = icon_map.get(msg_type, ICONS['info'])
    
    st.markdown(
        f'<div class="{msg_type}-msg">{icon} {msg_text}</div>', 
        unsafe_allow_html=True
    )
    
    # 清除訊息
    st.session_state.message = None


# ==================== 除錯工具 ====================

def display_debug_info():
    """顯示除錯資訊 (完整版)"""
    if not (st.session_state.get('show_debug', False) and st.session_state.get('data_loaded', False)):
        return
    
    st.markdown('<div class="debug-box">', unsafe_allow_html=True)
    st.subheader(f"{ICONS['search']} 除錯資訊")
    
    debug_tab1, debug_tab2, debug_tab3 = st.tabs([
        f"{ICONS['box']} 物料總覽", 
        f"{ICONS['item']} 物品清單", 
        f"{ICONS['transaction']} 交易紀錄"
    ])
    
    with debug_tab1:
        _display_sheet_debug('boxes')
        _display_field_mapping_check('boxes')
    
    with debug_tab2:
        _display_sheet_debug('items')
        _display_field_mapping_check('items')
    
    with debug_tab3:
        _display_sheet_debug('transactions')
        _display_field_mapping_check('transactions')
    
    st.markdown('</div>', unsafe_allow_html=True)


def _display_sheet_debug(data_type):
    """顯示單個工作表的除錯資訊 (優化版)"""
    st.write("**📋 實際標題列:**")
    headers_key = f'debug_{data_type}_headers'
    if hasattr(st.session_state, headers_key):
        headers = getattr(st.session_state, headers_key)
        if headers:
            headers_df = pd.DataFrame(
                [headers], 
                columns=[f"欄位{i+1}" for i in range(len(headers))]
            )
            st.dataframe(headers_df, use_container_width=True)
        else:
            st.warning("無標題列資料")
    
    st.write("**📄 原始資料 (前3筆):**")
    raw_key = f'debug_{data_type}_raw'
    if hasattr(st.session_state, raw_key):
        raw_data = getattr(st.session_state, raw_key)
        if raw_data:
            st.dataframe(pd.DataFrame(raw_data), use_container_width=True)
        else:
            st.warning("無原始資料")
    
    st.write("**✅ 標準化後資料 (前3筆):**")
    normalized_key = f'debug_{data_type}_normalized'
    if hasattr(st.session_state, normalized_key):
        normalized_data = getattr(st.session_state, normalized_key)
        if normalized_data:
            st.dataframe(pd.DataFrame(normalized_data), use_container_width=True)
        else:
            st.warning("無標準化資料")


def _display_field_mapping_check(data_type):
    """顯示欄位映射檢查結果 (優化版)"""
    st.write("**🔍 欄位映射檢查:**")
    headers_key = f'debug_{data_type}_headers'
    
    if not hasattr(st.session_state, headers_key):
        st.warning("無標題列資料,無法檢查映射")
        return
    
    headers = getattr(st.session_state, headers_key)
    if not headers:
        st.warning("標題列為空")
        return
    
    mapping_result = {}
    for std_name, possible_names in FIELD_MAPPING[data_type].items():
        found = None
        for name in possible_names:
            if name in headers:
                found = name
                break
        mapping_result[std_name] = found or "❌ 未找到"
    
    mapping_df = pd.DataFrame(
        list(mapping_result.items()), 
        columns=['標準欄位', '對應到的欄位']
    )
    st.dataframe(mapping_df, use_container_width=True)
    
    # 檢查是否有未映射的欄位
    unmapped = [k for k, v in mapping_result.items() if v == "❌ 未找到"]
    if unmapped:
        st.error(f"⚠️ 以下欄位未找到對應: {', '.join(unmapped)}")


# ==================== 統計資訊顯示 ====================

def display_metrics(col_info):
    """顯示統計指標 (使用圖示)"""
    if st.session_state.get('data_loaded', False):
        col_a, col_b, col_c = col_info.columns(3)
        with col_a:
            st.metric(
                f"{ICONS['box']} Boxes", 
                len(st.session_state.get('boxes_data', []))
            )
        with col_b:
            st.metric(
                f"{ICONS['item']} Items", 
                len(st.session_state.get('items_data', []))
            )
        with col_c:
            st.metric(
                f"{ICONS['transaction']} Logs", 
                len(st.session_state.get('transactions_data', []))
            )
    else:
        col_info.markdown(
            f'<div class="info-box">{ICONS["info"]} 請點擊「載入資料」按鈕從 Google Sheets 讀取資料</div>', 
            unsafe_allow_html=True
        )


def display_sidebar_stats():
    """顯示側邊欄統計資訊 (完整版)"""
    with st.sidebar:
        st.header(f"{ICONS['storage']} 系統統計")
        
        boxes_count = len(st.session_state.get('boxes_data', []))
        items_count = len(st.session_state.get('items_data', []))
        total_qty = sum(item.get('Quantity', 0) for item in st.session_state.get('items_data', []))
        trans_count = len(st.session_state.get('transactions_data', []))
        
        st.metric(f"{ICONS['box']} 總 Box 數", boxes_count)
        st.metric(f"{ICONS['item']} 總物品種類", items_count)
        st.metric(f"{ICONS['storage']} 總庫存數量", total_qty)
        st.metric(f"{ICONS['transaction']} 交易記錄數", trans_count)
        
        # 顯示低庫存警告
        low_stock_items = [
            item for item in st.session_state.get('items_data', [])
            if item.get('Quantity', 0) < 5 and item.get('Quantity', 0) > 0
        ]
        
        if low_stock_items:
            st.divider()
            st.warning(f"{ICONS['warning']} 低庫存警告")
            st.caption(f"有 {len(low_stock_items)} 項物品庫存不足 5 件")


# ==================== 調撥表單元件 ====================

def render_transfer_form(spreadsheet):
    """渲染調撥入庫表單"""
    st.markdown('<div class="transfer-section">', unsafe_allow_html=True)
    st.subheader(f"{ICONS['transfer_in']} 調撥入庫")
    
    with st.form("transfer_form"):
        # ===== 來源物品 =====
        st.markdown(f"### {ICONS['transfer_out']} 來源物品")
        col1, col2 = st.columns(2)
        
        with col1:
            # 選擇來源物品
            source_options = [
                f"{item.get('SN', '')} - {item.get('ItemName', '')} ({item.get('BoxID', '')})" 
                for item in st.session_state.get('items_data', [])
                if item.get('SN') and item.get('ItemName')
            ]
            source_item = st.selectbox(
                "來源物品 *", 
                [""] + source_options, 
                key="transfer_source"
            )
            
        with col2:
            trans_qty = st.number_input(
                "調撥數量 *", 
                min_value=1, 
                value=1, 
                key="transfer_qty"
            )
            
            # 顯示來源物品庫存
            if source_item:
                source_sn = source_item.split(" - ")[0]
                source_data = next(
                    (i for i in st.session_state.get('items_data', []) 
                     if i.get('SN') == source_sn), 
                    None
                )
                if source_data:
                    current_qty = source_data.get('Quantity', 0)
                    if current_qty >= trans_qty:
                        st.success(f"{ICONS['storage']} 當前庫存: {current_qty} 件 (充足)")
                    else:
                        st.error(f"{ICONS['warning']} 當前庫存: {current_qty} 件 (不足)")
        
        st.divider()
        
        # ===== 目標位置 =====
        st.markdown(f"### {ICONS['transfer_in']} 目標位置")
        
        # 選擇調撥模式
        transfer_mode = st.radio(
            "調撥模式",
            ["調撥到既有物品", "調撥到新位置"],
            horizontal=True,
            key="transfer_mode",
            help="「既有物品」會增加目標物品庫存;「新位置」會建立新的物品記錄"
        )
        
        if transfer_mode == "調撥到既有物品":
            # 模式 1: 調撥到既有物品
            col3, col4 = st.columns(2)
            
            with col3:
                target_options = [
                    f"{item.get('SN', '')} - {item.get('ItemName', '')} ({item.get('BoxID', '')})" 
                    for item in st.session_state.get('items_data', [])
                    if item.get('SN') and item.get('ItemName')
                ]
                target_item = st.selectbox(
                    "目標物品 *", 
                    [""] + target_options, 
                    key="transfer_target"
                )
            
            with col4:
                # 顯示目標物品資訊
                if target_item:
                    target_sn = target_item.split(" - ")[0]
                    target_data = next(
                        (i for i in st.session_state.get('items_data', []) 
                         if i.get('SN') == target_sn), 
                        None
                    )
                    if target_data:
                        st.info(f"{ICONS['storage']} 目標庫存: {target_data.get('Quantity', 0)} 件")
                        st.caption(f"📍 位置: {target_data.get('Location', '未設定')}")
                        st.caption(f"{ICONS['box']} 容器: {target_data.get('BoxID', '未設定')}")
            
            target_box = None
            target_location = None
        
        else:
            # 模式 2: 調撥到新位置
            target_item = None
            
            col3, col4 = st.columns(2)
            
            with col3:
                box_options = [
                    box.get('BoxID', '') 
                    for box in st.session_state.get('boxes_data', [])
                    if box.get('BoxID')
                ]
                target_box = st.selectbox(
                    f"{ICONS['box']} 目標容器 *", 
                    [""] + box_options, 
                    key="transfer_target_box"
                )
            
            with col4:
                target_location = st.text_input(
                    "📍 目標位置", 
                    placeholder="例如: A-01", 
                    key="transfer_target_location"
                )
            
            st.info(f"{ICONS['info']} 系統將自動建立新的物品記錄,物品名稱和規格將繼承自來源物品")
        
        st.divider()
        
        # ===== 其他資訊 =====
        col5, col6 = st.columns(2)
        with col5:
            trans_operator = st.text_input(
                "👤 操作人員", 
                placeholder="姓名", 
                key="transfer_operator"
            )
        
        with col6:
            trans_remark = st.text_area(
                "📝 備註", 
                placeholder="調撥原因說明", 
                height=100, 
                key="transfer_remark"
            )
        
        # ===== 提交按鈕 =====
        col_submit, col_cancel = st.columns([1, 5])
        
        with col_submit:
            submitted = st.form_submit_button(
                f"{ICONS['transfer_in']} 執行調撥", 
                width="stretch", 
                type="primary"
            )
        
        with col_cancel:
            cancelled = st.form_submit_button("取消", width="stretch")
        
        # ===== 處理表單提交 =====
        if submitted:
            # 驗證必填欄位
            if not source_item:
                st.error(f"{ICONS['error']} 請選擇來源物品")
            elif transfer_mode == "調撥到既有物品" and not target_item:
                st.error(f"{ICONS['error']} 請選擇目標物品")
            elif transfer_mode == "調撥到新位置" and not target_box:
                st.error(f"{ICONS['error']} 請選擇目標容器")
            else:
                # 執行調撥
                source_sn = source_item.split(" - ")[0]
                
                if transfer_mode == "調撥到既有物品":
                    target_sn = target_item.split(" - ")[0]
                else:
                    target_sn = None  # 將建立新物品
                
                from data_operations import execute_transaction
                
                success, message = execute_transaction(
                    spreadsheet=spreadsheet,
                    trans_sn=source_sn,
                    trans_action='調撥入庫',
                    trans_qty=trans_qty,
                    trans_operator=trans_operator,
                    trans_remark=trans_remark,
                    target_sn=target_sn,
                    target_box=target_box,
                    target_location=target_location
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"{ICONS['error']} {message}")
        
        if cancelled:
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_box_transfer_form(spreadsheet):
    """渲染容器間調撥表單 (Box to Box)"""
    st.markdown('<div class="transfer-section">', unsafe_allow_html=True)
    st.subheader(f"{ICONS['box']} 容器間調撥 (Box → Box)")
    st.caption("在不同容器(Box)之間調撥物品")
    
    with st.form("box_transfer_form"):
        # ===== 步驟 1: 選擇來源容器 =====
        st.markdown(f"### {ICONS['transfer_out']} 步驟 1: 選擇來源容器")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 取得所有 Box 選項
            box_options = [
                f"{box.get('BoxID', '')} - {box.get('Description', '')} ({box.get('Category', '')})"
                for box in st.session_state.get('boxes_data', [])
                if box.get('BoxID')
            ]
            
            source_box = st.selectbox(
                f"{ICONS['box']} 來源容器 *",
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
                    item for item in st.session_state.get('items_data', [])
                    if item.get('BoxID') == source_box_id and item.get('Quantity', 0) > 0
                ]
                
                if items_in_box:
                    st.success(f"{ICONS['storage']} 容器內有 {len(items_in_box)} 種物品")
                    
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
                    st.warning(f"{ICONS['warning']} 此容器內沒有物品或物品庫存為 0")
        
        st.divider()
        
        # ===== 步驟 2: 選擇要調撥的物品 =====
        st.markdown(f"### 📦 步驟 2: 選擇要調撥的物品")
        
        if source_box:
            source_box_id = source_box.split(" - ")[0]
            items_in_box = [
                item for item in st.session_state.get('items_data', [])
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
                st.warning(f"{ICONS['warning']} 請先選擇有物品的來源容器")
                selected_item = None
        else:
            st.info(f"{ICONS['info']} 請先選擇來源容器")
            selected_item = None
        
        st.divider()
        
        # ===== 步驟 3: 選擇目標容器 =====
        st.markdown(f"### {ICONS['transfer_in']} 步驟 3: 選擇目標容器")
        
        col5, col6 = st.columns(2)
        
        with col5:
            # 目標容器選項 (排除來源容器)
            target_box_options = [
                f"{box.get('BoxID', '')} - {box.get('Description', '')} ({box.get('Category', '')})"
                for box in st.session_state.get('boxes_data', [])
                if box.get('BoxID') and (not source_box or box.get('BoxID') != source_box.split(" - ")[0])
            ]
            
            target_box = st.selectbox(
                f"{ICONS['box']} 目標容器 *",
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
                    (b for b in st.session_state.get('boxes_data', []) 
                     if b.get('BoxID') == target_box_id),
                    None
                )
                if target_box_data:
                    st.caption(f"負責人: {target_box_data.get('Owner', '未設定')}")
                    st.caption(f"狀態: {target_box_data.get('Status', '未設定')}")
        
        st.divider()
        
        # ===== 步驟 4: 調撥模式 =====
        st.markdown("### ⚙️ 步驟 4: 調撥模式")
        
        transfer_mode = st.radio(
            "選擇調撥方式",
            ["合併到目標容器既有物品", "在目標容器建立新物品"],
            key="box_transfer_mode",
            help="「合併」會增加目標容器內同物品的庫存;「新建」會在目標容器建立新的物品記錄"
        )
        
        # 如果選擇合併模式,顯示目標容器內可合併的物品
        target_item = None
        if transfer_mode == "合併到目標容器既有物品" and target_box and selected_item:
            target_box_id = target_box.split(" - ")[0]
            selected_sn = selected_item.split(" - ")[0]
            selected_data = next(
                (i for i in st.session_state.get('items_data', []) 
                 if i.get('SN') == selected_sn),
                None
            )
            
            if selected_data:
                # 在目標容器中找同名物品
                matching_items = [
                    item for item in st.session_state.get('items_data', [])
                    if (item.get('BoxID') == target_box_id and 
                        item.get('ItemName') == selected_data.get('ItemName') and
                        item.get('SN') != selected_sn)
                ]
                
                if matching_items:
                    target_item_options = [
                        f"{item.get('SN', '')} - {item.get('ItemName', '')} (庫存: {item.get('Quantity', 0)})"
                        for item in matching_items
                    ]
                    
                    target_item = st.selectbox(
                        "選擇要合併的目標物品",
                        [""] + target_item_options,
                        key="box_transfer_target_item",
                        help="目標容器內同名的物品"
                    )
                else:
                    st.warning(f"{ICONS['warning']} 目標容器內沒有同名物品,建議選擇「建立新物品」模式")
        
        st.divider()
        
        # ===== 其他資訊 =====
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
                f"{ICONS['transfer_in']} 執行調撥",
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
                st.error(f"{ICONS['error']} 請選擇來源容器")
            elif not selected_item:
                st.error(f"{ICONS['error']} 請選擇要調撥的物品")
            elif not target_box:
                st.error(f"{ICONS['error']} 請選擇目標容器")
            elif transfer_mode == "合併到目標容器既有物品" and not target_item:
                st.error(f"{ICONS['error']} 請選擇目標物品,或切換為「建立新物品」模式")
            else:
                # 執行調撥
                source_sn = selected_item.split(" - ")[0]
                target_box_id = target_box.split(" - ")[0]
                
                if transfer_mode == "合併到目標容器既有物品":
                    target_sn = target_item.split(" - ")[0]
                else:
                    target_sn = None  # 建立新物品
                
                from data_operations import execute_transaction
                
                success, message = execute_transaction(
                    spreadsheet=spreadsheet,
                    trans_sn=source_sn,
                    trans_action='調撥入庫',
                    trans_qty=transfer_qty,
                    trans_operator=operator,
                    trans_remark=remark,
                    target_sn=target_sn,
                    target_box=target_box_id,
                    target_location=target_location
                )
                
                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"{ICONS['error']} {message}")
        
        if cancelled:
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


# ==================== 頁面標題 ====================

def render_page_header():
    """渲染頁面標題"""
    st.markdown(f"""
    <div class="main-header">
        <h1 style="margin:0; font-size: 2.5rem;">{ICONS['box']} 物料管理系統</h1>
        <p style="margin:0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.95;">
            Google Sheets 整合 | 進階搜尋 | 編輯管理 | 批次匯入匯出 | 調撥管理
        </p>
    </div>
    """, unsafe_allow_html=True)