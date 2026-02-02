"""
物料管理系統 - Streamlit 主程式（優化版）
根據三層架構重新設計：Material Overview (容器) -> Item List (物品) -> Transaction Log (交易)
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 導入模組 ====================
try:
    from data_operations import (
        ItemOperations,
        TransactionLogOperations,
        MaterialOverviewOperations
    )
    DB_AVAILABLE = True
    logger.info("✅ 資料庫模組載入成功")
except ImportError as e:
    logger.error(f"無法導入資料庫模組: {e}")
    DB_AVAILABLE = False

# Icon 定義
ICONS = {
    'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️',
    'box': '📦', 'item': '📋', 'transaction': '📝', 'storage': '🗄️',
    'search': '🔍', 'transfer_in': '📥', 'transfer_out': '📤',
    'container': '🎁', 'project': '📂', 'chart': '📊'
}

# ==================== 頁面配置 ====================
st.set_page_config(
    page_title="物料管理系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂樣式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .action-card {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .section-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 Session State ====================
def init_session_state():
    defaults = {
        'message': None,
        'current_page': 'dashboard',
        'show_debug': False,
        'selected_box': None,
        'selected_item': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ==================== 輔助函數 ====================
def show_message(msg_type, msg_text):
    """顯示訊息"""
    icons = {'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
    icon = icons.get(msg_type, 'ℹ️')
    
    msg_funcs = {
        'success': st.success,
        'error': st.error,
        'warning': st.warning,
        'info': st.info
    }
    msg_funcs.get(msg_type, st.info)(f"{icon} {msg_text}")

def display_messages():
    """顯示存儲的訊息"""
    if st.session_state.message:
        msg = st.session_state.message
        show_message(msg['type'], msg['text'])
        st.session_state.message = None

# ==================== 側邊欄 ====================
def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem;">
            <h1 style="color: #667eea;">{ICONS['box']} 物料管理</h1>
            <p style="color: #64748b; font-size: 0.9rem;">三層架構管理系統</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 功能選單
        menu_options = {
            f"{ICONS['chart']} 儀表板": "dashboard",
            f"{ICONS['container']} 容器管理": "boxes",
            f"{ICONS['item']} 物料列表": "items",
            f"{ICONS['success']} 新增物料": "add_item",
            f"{ICONS['transaction']} 庫存異動": "stock_operations",
            f"{ICONS['search']} 搜尋查詢": "search",
            f"{ICONS['storage']} 交易記錄": "transactions"
        }
        
        selected = st.radio(
            "選擇功能",
            list(menu_options.keys()),
            label_visibility="collapsed"
        )
        
        st.session_state.current_page = menu_options[selected]
        
        st.markdown("---")
        
        # 系統狀態
        if DB_AVAILABLE:
            st.success(f"{ICONS['success']} 資料庫已連接")
            
            try:
                stats = MaterialOverviewOperations.get_statistics()
                
                st.markdown("### 📊 即時統計")
                st.metric("容器總數", stats.get('total_boxes', 0))
                st.metric("物料總數", stats.get('total_items', 0))
                st.metric("總庫存量", f"{stats.get('total_quantity', 0):,}")
                
                if stats.get('low_stock_count', 0) > 0:
                    st.warning(f"{ICONS['warning']} {stats.get('low_stock_count', 0)} 項低庫存")
                
                if stats.get('zero_stock_count', 0) > 0:
                    st.error(f"🔴 {stats.get('zero_stock_count', 0)} 項零庫存")
            except Exception as e:
                st.error(f"統計錯誤: {e}")
        else:
            st.error(f"{ICONS['error']} 資料庫未連接")
        
        st.markdown("---")
        st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==================== 頁面: 儀表板 ====================
def page_dashboard():
    """儀表板頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['chart']} 物料管理系統儀表板</h1>
        <p>三層架構：容器 → 物料 → 交易記錄</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    # 獲取統計資訊
    stats = MaterialOverviewOperations.get_statistics()
    
    # 關鍵指標
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label=f"{ICONS['container']} 容器總數",
            value=stats.get('total_boxes', 0)
        )
    
    with col2:
        st.metric(
            label=f"{ICONS['item']} 物料總數",
            value=stats.get('total_items', 0)
        )
    
    with col3:
        st.metric(
            label=f"{ICONS['storage']} 總庫存量",
            value=f"{stats.get('total_quantity', 0):,}"
        )
    
    with col4:
        st.metric(
            label=f"{ICONS['warning']} 低庫存",
            value=stats.get('low_stock_count', 0),
            delta_color="inverse"
        )
    
    with col5:
        st.metric(
            label="🔴 零庫存",
            value=stats.get('zero_stock_count', 0),
            delta_color="inverse"
        )
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # 雙欄顯示
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader(f"{ICONS['container']} 容器/專案概覽")
        boxes = MaterialOverviewOperations.get_all_boxes(limit=10)
        if boxes:
            df = pd.DataFrame(boxes)
            st.dataframe(df, use_container_width=True, hide_index=True, height=350)
        else:
            st.info("目前沒有容器資料")
    
    with col_right:
        st.subheader(f"{ICONS['transaction']} 最近交易記錄")
        transactions = TransactionLogOperations.get_transactions(limit=10)
        if transactions:
            df = pd.DataFrame(transactions)
            # 只顯示關鍵欄位
            display_cols = ['ActionType', 'TransQty', 'StockBefore', 'StockAfter', 'Operator', 'Timestamp']
            available_cols = [col for col in display_cols if col in df.columns]
            st.dataframe(df[available_cols], use_container_width=True, hide_index=True, height=350)
        else:
            st.info("目前沒有交易記錄")

# ==================== 頁面: 容器管理 ====================
def page_boxes():
    """容器管理頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['container']} 容器/專案管理</h1>
        <p>管理物料的容器和專案分類</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    # 操作區
    tab1, tab2, tab3 = st.tabs(["📋 容器列表", "➕ 新增容器", "📊 容器統計"])
    
    with tab1:
        st.subheader("所有容器/專案")
        boxes = MaterialOverviewOperations.get_all_boxes()
        
        if boxes:
            df = pd.DataFrame(boxes)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
            
            # 選擇容器查看詳情
            st.markdown("---")
            st.subheader("查看容器內物料")
            
            box_options = [f"{box['BoxID']} - {box.get('Description', 'N/A')}" for box in boxes]
            selected_box = st.selectbox("選擇容器", box_options)
            
            if selected_box:
                box_id = selected_box.split(" - ")[0]
                items = ItemOperations.get_items_by_box(box_id)
                
                if items:
                    st.success(f"找到 {len(items)} 項物料")
                    df_items = pd.DataFrame(items)
                    st.dataframe(df_items, use_container_width=True, hide_index=True)
                else:
                    st.info(f"容器 {box_id} 目前沒有物料")
        else:
            st.warning("目前沒有容器資料")
    
    with tab2:
        st.subheader("新增容器/專案")
        
        with st.form("add_box_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                box_id = st.text_input("容器ID *", placeholder="例如: BOX001")
                category = st.text_input("分類", placeholder="例如: 電子元件")
            
            with col2:
                owner = st.text_input("負責人", placeholder="例如: 張三")
                status = st.selectbox("狀態", ["Active", "Inactive", "Archived"])
            
            description = st.text_area("描述", placeholder="容器的詳細說明")
            
            submitted = st.form_submit_button(f"{ICONS['success']} 新增容器", type="primary")
            
            if submitted:
                if not box_id:
                    st.error("請填寫容器ID")
                else:
                    box_data = {
                        'BoxID': box_id,
                        'Category': category,
                        'Description': description,
                        'Owner': owner,
                        'Status': status
                    }
                    
                    if MaterialOverviewOperations.add_box(box_data):
                        st.session_state.message = {
                            'type': 'success',
                            'text': f'容器 {box_id} 新增成功'
                        }
                        st.rerun()
                    else:
                        st.error("新增失敗")
    
    with tab3:
        st.subheader("容器統計分析")
        stats = MaterialOverviewOperations.get_statistics()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("容器總數", stats.get('total_boxes', 0))
        with col2:
            st.metric("物料總數", stats.get('total_items', 0))

# ==================== 頁面: 物料列表 ====================
def page_items():
    """物料列表頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['item']} 物料列表管理</h1>
        <p>查看和管理所有物料庫存</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    # 控制選項
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        limit = st.slider("顯示數量", 10, 1000, 100, 10)
    with col2:
        if st.button(f"{ICONS['search']} 重新整理", use_container_width=True):
            st.rerun()
    with col3:
        export = st.button("📥 匯出 CSV", use_container_width=True)
    
    # 獲取物料列表
    items = ItemOperations.get_all_items(limit=limit)
    
    if items:
        df = pd.DataFrame(items)
        
        if export:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="下載 CSV 檔案",
                data=csv,
                file_name=f"items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)
        st.info(f"共顯示 {len(items)} 筆物料")
        
        # 物料操作區
        st.markdown("---")
        st.subheader(f"{ICONS['box']} 快速操作")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📝 編輯物料**")
            item_options = [f"{item['SN']} - {item['ItemName']}" for item in items]
            selected = st.selectbox("選擇物料", item_options, key="edit_item")
            
            if st.button("查看詳細資訊", use_container_width=True):
                sn = selected.split(" - ")[0]
                item = ItemOperations.get_item_by_sn(sn)
                if item:
                    st.json(item)
        
        with col2:
            st.markdown("**🗑️ 刪除物料**")
            delete_item = st.selectbox("選擇要刪除的物料", item_options, key="del_item")
            
            if st.button("🗑️ 刪除", type="secondary", use_container_width=True):
                sn = delete_item.split(" - ")[0]
                if ItemOperations.delete_item(sn):
                    st.session_state.message = {'type': 'success', 'text': '刪除成功'}
                    st.rerun()
    else:
        st.warning("目前沒有物料資料")

# ==================== 頁面: 新增物料 ====================
def page_add_item():
    """新增物料頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['success']} 新增物料</h1>
        <p>建立新的物料記錄到資料庫</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    with st.form("add_item_form", clear_on_submit=True):
        st.subheader("📋 物料基本資訊")
        
        col1, col2 = st.columns(2)
        
        with col1:
            item_name = st.text_input("物料名稱 *", placeholder="請輸入物料名稱")
            spec = st.text_input("規格", placeholder="例如: 100mm x 50mm")
            location = st.text_input("儲存位置", placeholder="例如: A01, B02")
        
        with col2:
            # 獲取容器列表
            boxes = MaterialOverviewOperations.get_all_boxes()
            box_options = [""] + [f"{box['BoxID']} - {box.get('Description', '')}" for box in boxes]
            
            box_select = st.selectbox("選擇容器 *", box_options)
            quantity = st.number_input("初始數量 *", min_value=0, value=0)
            operator = st.text_input("操作人員", value="Admin")
        
        remark = st.text_area("備註", placeholder="可選：新增物料的原因或其他說明", height=100)
        
        submitted = st.form_submit_button(f"{ICONS['success']} 新增物料", use_container_width=True, type="primary")
        
        if submitted:
            if not item_name:
                st.error("請填寫物料名稱")
            elif not box_select:
                st.error("請選擇容器")
            else:
                box_id = box_select.split(" - ")[0]
                
                item_data = {
                    'ItemName': item_name,
                    'Spec': spec,
                    'Location': location,
                    'BoxID': box_id,
                    'Quantity': quantity
                }
                
                if ItemOperations.add_item(item_data):
                    st.session_state.message = {
                        'type': 'success',
                        'text': f'物料「{item_name}」新增成功'
                    }
                    st.balloons()
                    st.rerun()
                else:
                    st.error("新增失敗")

# ==================== 頁面: 庫存異動 ====================
def page_stock_operations():
    """庫存異動頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['transaction']} 庫存異動操作</h1>
        <p>入庫 | 出庫 | 調撥</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    tab1, tab2, tab3 = st.tabs(["📥 入庫", "📤 出庫", "🔄 調撥"])
    
    # 獲取物料和容器列表
    items = ItemOperations.get_all_items(limit=500)
    boxes = MaterialOverviewOperations.get_all_boxes()
    
    if not items:
        st.warning("⚠️ 請先新增物料才能進行庫存異動操作")
        return
    
    # 準備物料選項（顯示詳細資訊）
    item_options = []
    for item in items:
        current_box = item.get('BoxID', '未指定')
        current_qty = item.get('Quantity', 0)
        item_options.append(f"{item['SN']} - {item['ItemName']} | 目前庫存: {current_qty} | 容器: {current_box}")
    
    # 準備容器選項（顯示詳細資訊）
    box_options = ["0 - 外部/其他來源"]
    for box in boxes:
        desc = box.get('Description', box.get('Category', ''))
        box_options.append(f"{box['BoxID']} - {desc}" if desc else box['BoxID'])
    
    # ==================== Tab 1: 入庫 ====================
    with tab1:
        st.subheader("📥 入庫作業")
        st.info("💡 入庫：從外部或其他來源將物料存入指定容器，增加庫存數量")
        
        with st.form("stock_in_form"):
            st.markdown("### 📦 物料資訊")
            
            selected_item = st.selectbox(
                "選擇物料 *",
                item_options,
                key="in_item",
                help="選擇要入庫的物料"
            )
            
            # 顯示選中物料的當前資訊
            if selected_item:
                sn = selected_item.split(" - ")[0]
                item = ItemOperations.get_item_by_sn(sn)
                if item:
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("當前庫存", item['Quantity'])
                    with col_b:
                        st.metric("當前容器", item.get('BoxID', 'N/A'))
                    with col_c:
                        st.metric("儲存位置", item.get('Location', 'N/A'))
            
            st.markdown("---")
            st.markdown("### 🎁 容器設定")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 來源容器（入庫通常從外部來源）
                from_box_select = st.selectbox(
                    "📤 來源容器 (FromBoxID)",
                    box_options,
                    index=0,  # 預設選擇"外部"
                    key="in_from_box",
                    help="入庫來源，通常選擇「外部/其他來源」"
                )
            
            with col2:
                # 目標容器（物料要存入的容器）
                to_box_select = st.selectbox(
                    "📥 目標容器 (ToBoxID) *",
                    box_options[1:],  # 排除"外部"選項
                    key="in_to_box",
                    help="物料要存入的目標容器"
                )
            
            st.markdown("---")
            st.markdown("### 📝 操作資訊")
            
            col1, col2 = st.columns(2)
            
            with col1:
                quantity = st.number_input(
                    "入庫數量 *",
                    min_value=1,
                    value=1,
                    key="in_qty",
                    help="要增加的庫存數量"
                )
            
            with col2:
                operator = st.text_input(
                    "操作人員 *",
                    value="Admin",
                    key="in_op",
                    help="執行入庫操作的人員姓名"
                )
            
            remark = st.text_area(
                "備註",
                placeholder="入庫原因、供應商、採購單號等資訊...",
                key="in_remark",
                height=100
            )
            
            st.markdown("---")
            submitted = st.form_submit_button("✅ 執行入庫", type="primary", use_container_width=True)
        
        if submitted:
            sn = selected_item.split(" - ")[0]
            to_box_id = to_box_select.split(" - ")[0]
            from_box_id = from_box_select.split(" - ")[0]
            
            if TransactionLogOperations.stock_in(sn, quantity, to_box_id, operator, remark):
                st.session_state.message = {
                    'type': 'success',
                    'text': f'✅ 入庫成功！物料已存入容器 {to_box_id}，數量 +{quantity}'
                }
                st.rerun()
            else:
                st.error("❌ 入庫失敗，請檢查資料是否正確")
    
    # ==================== Tab 2: 出庫 ====================
    with tab2:
        st.subheader("📤 出庫作業")
        st.info("💡 出庫：從指定容器取出物料，減少庫存數量")
        
        with st.form("stock_out_form"):
            st.markdown("### 📦 物料資訊")
            
            selected_item = st.selectbox(
                "選擇物料 *",
                item_options,
                key="out_item",
                help="選擇要出庫的物料"
            )
            
            # 顯示選中物料的當前資訊
            if selected_item:
                sn = selected_item.split(" - ")[0]
                item = ItemOperations.get_item_by_sn(sn)
                if item:
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        current_qty = item['Quantity']
                        st.metric("當前庫存", current_qty)
                        if current_qty == 0:
                            st.error("⚠️ 庫存為 0")
                    with col_b:
                        st.metric("當前容器", item.get('BoxID', 'N/A'))
                    with col_c:
                        st.metric("儲存位置", item.get('Location', 'N/A'))
            
            st.markdown("---")
            st.markdown("### 🎁 容器設定")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 來源容器（物料從哪個容器取出）
                from_box_select = st.selectbox(
                    "📤 來源容器 (FromBoxID) *",
                    box_options[1:],  # 排除"外部"選項
                    key="out_from_box",
                    help="物料要從哪個容器取出"
                )
            
            with col2:
                # 目標容器（出庫通常是外部）
                to_box_select = st.selectbox(
                    "📥 目標容器 (ToBoxID)",
                    box_options,
                    index=0,  # 預設選擇"外部"
                    key="out_to_box",
                    help="出庫目標，通常選擇「外部/其他來源」"
                )
            
            st.markdown("---")
            st.markdown("### 📝 操作資訊")
            
            col1, col2 = st.columns(2)
            
            with col1:
                quantity = st.number_input(
                    "出庫數量 *",
                    min_value=1,
                    value=1,
                    key="out_qty",
                    help="要減少的庫存數量"
                )
            
            with col2:
                operator = st.text_input(
                    "操作人員 *",
                    value="Admin",
                    key="out_op",
                    help="執行出庫操作的人員姓名"
                )
            
            remark = st.text_area(
                "備註",
                placeholder="出庫用途、領用部門、工單號碼等資訊...",
                key="out_remark",
                height=100
            )
            
            st.markdown("---")
            submitted = st.form_submit_button("✅ 執行出庫", type="primary", use_container_width=True)
        
        if submitted:
            sn = selected_item.split(" - ")[0]
            from_box_id = from_box_select.split(" - ")[0]
            
            if TransactionLogOperations.stock_out(sn, quantity, from_box_id, operator, remark):
                st.session_state.message = {
                    'type': 'success',
                    'text': f'✅ 出庫成功！從容器 {from_box_id} 取出，數量 -{quantity}'
                }
                st.rerun()
            else:
                st.error("❌ 出庫失敗，請檢查庫存是否足夠")
    
    # ==================== Tab 3: 調撥 ====================
    with tab3:
        st.subheader("🔄 調撥作業")
        st.info("💡 調撥：將物料從一個容器移動到另一個容器，庫存總量不變")
        
        with st.form("transfer_form"):
            st.markdown("### 📦 物料資訊")
            
            selected_item = st.selectbox(
                "選擇物料 *",
                item_options,
                key="trans_item",
                help="選擇要調撥的物料"
            )
            
            # 顯示選中物料的當前資訊
            if selected_item:
                sn = selected_item.split(" - ")[0]
                item = ItemOperations.get_item_by_sn(sn)
                if item:
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("當前庫存", item['Quantity'])
                    with col_b:
                        st.metric("當前容器", item.get('BoxID', 'N/A'))
                    with col_c:
                        st.metric("儲存位置", item.get('Location', 'N/A'))
            
            st.markdown("---")
            st.markdown("### 🎁 容器設定")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 來源容器
                from_box_select = st.selectbox(
                    "📤 來源容器 (FromBoxID) *",
                    box_options[1:],  # 排除"外部"選項
                    key="trans_from_box",
                    help="物料目前所在的容器"
                )
            
            with col2:
                # 目標容器
                to_box_select = st.selectbox(
                    "📥 目標容器 (ToBoxID) *",
                    box_options[1:],  # 排除"外部"選項
                    key="trans_to_box",
                    help="物料要移動到的目標容器"
                )
            
            # 檢查是否選擇了相同容器
            if from_box_select == to_box_select:
                st.warning("⚠️ 來源容器和目標容器不能相同！")
            
            st.markdown("---")
            st.markdown("### 📝 操作資訊")
            
            col1, col2 = st.columns(2)
            
            with col1:
                quantity = st.number_input(
                    "調撥數量 *",
                    min_value=1,
                    value=1,
                    key="trans_qty",
                    help="要調撥的數量（庫存總量不變）"
                )
            
            with col2:
                operator = st.text_input(
                    "操作人員 *",
                    value="Admin",
                    key="trans_op",
                    help="執行調撥操作的人員姓名"
                )
            
            remark = st.text_area(
                "備註",
                placeholder="調撥原因、目的等資訊...",
                key="trans_remark",
                height=100
            )
            
            st.markdown("---")
            submitted = st.form_submit_button("✅ 執行調撥", type="primary", use_container_width=True)
        
        if submitted:
            sn = selected_item.split(" - ")[0]
            from_box_id = from_box_select.split(" - ")[0]
            to_box_id = to_box_select.split(" - ")[0]
            
            if from_box_id == to_box_id:
                st.error("❌ 來源容器和目標容器不能相同！")
            elif TransactionLogOperations.transfer(sn, quantity, from_box_id, to_box_id, operator, remark):
                st.session_state.message = {
                    'type': 'success',
                    'text': f'✅ 調撥成功！物料從 {from_box_id} 移動到 {to_box_id}，數量 {quantity}'
                }
                st.rerun()
            else:
                st.error("❌ 調撥失敗，請檢查資料是否正確")

# ==================== 頁面: 搜尋查詢 ====================
def page_search():
    """搜尋查詢頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['search']} 搜尋查詢</h1>
        <p>快速找到您需要的物料資訊</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        keyword = st.text_input("搜尋關鍵字", placeholder="輸入要搜尋的內容...")
    
    with col2:
        field = st.selectbox(
            "搜尋欄位",
            ["ItemName", "Spec", "Location", "BoxID", "SN"],
            format_func=lambda x: {
                "ItemName": "物料名稱",
                "Spec": "規格",
                "Location": "位置",
                "BoxID": "箱號",
                "SN": "序號"
            }.get(x, x)
        )
    
    with col3:
        search_btn = st.button(f"{ICONS['search']} 搜尋", use_container_width=True, type="primary")
    
    if search_btn and keyword:
        with st.spinner('搜尋中...'):
            results = ItemOperations.search_items(keyword, field)
            
            if results:
                st.success(f"找到 {len(results)} 筆結果")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載搜尋結果",
                    data=csv,
                    file_name=f"search_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning(f"沒有找到符合 '{keyword}' 的物料")

# ==================== 頁面: 交易記錄 ====================
def page_transactions():
    """交易記錄頁面"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{ICONS['storage']} 交易記錄管理</h1>
        <p>查看、篩選、分析所有物料異動歷史</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_messages()
    
    # 主要標籤頁
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 所有記錄", 
        "📊 分類統計", 
        "🔍 進階查詢",
        "➕ 手動記錄"
    ])
    
    # ==================== Tab 1: 所有記錄 ====================
    with tab1:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            limit = st.slider("顯示數量", 10, 500, 100, 10)
        with col2:
            if st.button(f"{ICONS['search']} 重新整理", use_container_width=True):
                st.rerun()
        with col3:
            show_all = st.checkbox("顯示全部欄位", value=False)
        
        transactions = TransactionLogOperations.get_transactions(limit=limit)
        
        if transactions:
            df = pd.DataFrame(transactions)
            
            # 快速統計卡片
            st.markdown("### 📊 快速統計")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總交易數", len(transactions))
            with col2:
                if 'TransQty' in df.columns:
                    st.metric("總異動量", f"{df['TransQty'].sum():,}")
            with col3:
                if 'ActionType' in df.columns:
                    action_count = df['ActionType'].nunique()
                    st.metric("操作類型", action_count)
            with col4:
                if 'Operator' in df.columns:
                    operator_count = df['Operator'].nunique()
                    st.metric("操作人員", operator_count)
            
            st.markdown("---")
            
            # 顯示表格
            if show_all:
                st.dataframe(df, use_container_width=True, hide_index=True, height=400)
            else:
                # 只顯示關鍵欄位
                key_cols = ['LogID', 'SN', 'ActionType', 'TransQty', 'StockBefore', 
                           'StockAfter', 'Operator', 'Timestamp']
                display_cols = [col for col in key_cols if col in df.columns]
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=400)
            
            # 匯出功能
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 匯出所有記錄 (CSV)",
                data=csv,
                file_name=f"transactions_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("目前沒有交易記錄")
    
    # ==================== Tab 2: 分類統計 ====================
    with tab2:
        st.subheader("📊 交易類型分析")
        
        transactions = TransactionLogOperations.get_transactions(limit=1000)
        
        if transactions:
            df = pd.DataFrame(transactions)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 按操作類型統計
                if 'ActionType' in df.columns:
                    st.markdown("#### 操作類型分布")
                    action_stats = df['ActionType'].value_counts().reset_index()
                    action_stats.columns = ['操作類型', '次數']
                    
                    st.dataframe(action_stats, use_container_width=True, hide_index=True)
                    st.bar_chart(action_stats.set_index('操作類型'))
            
            with col2:
                # 按操作人員統計
                if 'Operator' in df.columns:
                    st.markdown("#### 操作人員統計")
                    operator_stats = df['Operator'].value_counts().reset_index()
                    operator_stats.columns = ['操作人員', '操作次數']
                    
                    st.dataframe(operator_stats, use_container_width=True, hide_index=True)
                    st.bar_chart(operator_stats.set_index('操作人員'))
            
            st.markdown("---")
            
            # 詳細統計表
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📥 入庫統計")
                stock_in = df[df['ActionType'] == '入庫'] if 'ActionType' in df.columns else pd.DataFrame()
                if not stock_in.empty and 'TransQty' in stock_in.columns:
                    st.metric("入庫次數", len(stock_in))
                    st.metric("入庫總量", f"{stock_in['TransQty'].sum():,}")
                else:
                    st.info("無入庫記錄")
            
            with col2:
                st.markdown("#### 📤 出庫統計")
                stock_out = df[df['ActionType'] == '出庫'] if 'ActionType' in df.columns else pd.DataFrame()
                if not stock_out.empty and 'TransQty' in stock_out.columns:
                    st.metric("出庫次數", len(stock_out))
                    st.metric("出庫總量", f"{stock_out['TransQty'].sum():,}")
                else:
                    st.info("無出庫記錄")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🔄 調撥統計")
                transfer = df[df['ActionType'] == '調撥'] if 'ActionType' in df.columns else pd.DataFrame()
                if not transfer.empty and 'TransQty' in transfer.columns:
                    st.metric("調撥次數", len(transfer))
                    st.metric("調撥總量", f"{transfer['TransQty'].sum():,}")
                else:
                    st.info("無調撥記錄")
            
            with col2:
                st.markdown("#### 🗑️ 其他操作")
                other = df[~df['ActionType'].isin(['入庫', '出庫', '調撥'])] if 'ActionType' in df.columns else pd.DataFrame()
                if not other.empty:
                    st.metric("其他操作次數", len(other))
                    if 'TransQty' in other.columns:
                        st.metric("其他操作總量", f"{other['TransQty'].sum():,}")
                else:
                    st.info("無其他操作記錄")
        else:
            st.warning("目前沒有交易記錄可供分析")
    
    # ==================== Tab 3: 進階查詢 ====================
    with tab3:
        st.subheader("🔍 進階查詢篩選")
        
        # 獲取所有容器選項（包含詳細資訊）
        boxes = MaterialOverviewOperations.get_all_boxes()
        box_id_list = ["全部"]
        box_display_list = ["全部"]
        
        for box in boxes:
            box_id_list.append(box['BoxID'])
            # 顯示格式：BoxID - Description
            desc = box.get('Description', box.get('Category', ''))
            box_display_list.append(f"{box['BoxID']} - {desc}" if desc else box['BoxID'])
        
        # 獲取所有物料選項
        items = ItemOperations.get_all_items(limit=500)
        item_options = ["全部"] + [f"{item['SN']} - {item['ItemName']}" for item in items]
        
        # 獲取所有操作人員（從現有交易記錄中）
        all_transactions = TransactionLogOperations.get_transactions(limit=500)
        operators = ["全部"]
        if all_transactions:
            df_temp = pd.DataFrame(all_transactions)
            if 'Operator' in df_temp.columns:
                operators.extend(sorted(df_temp['Operator'].unique().tolist()))
        
        with st.form("advanced_search_form"):
            st.markdown("#### 🔍 篩選條件")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📦 物料與操作**")
                search_item = st.selectbox(
                    "選擇物料",
                    item_options,
                    help="選擇特定物料或查看全部"
                )
                
                search_action = st.multiselect(
                    "操作類型",
                    ['入庫', '出庫', '調撥', '報廢', '盤點', '退貨', '借出', '歸還'],
                    help="可多選，不選則顯示全部類型"
                )
                
                search_operator = st.selectbox(
                    "操作人員",
                    operators,
                    help="選擇特定操作人員或查看全部"
                )
            
            with col2:
                st.markdown("**🎁 容器篩選**")
                
                # FromBoxID 下拉選單
                from_box_index = st.selectbox(
                    "📤 來源容器 (FromBoxID)",
                    range(len(box_display_list)),
                    format_func=lambda x: box_display_list[x],
                    help="篩選特定來源容器的交易記錄",
                    key="from_box_select"
                )
                search_box_from = box_id_list[from_box_index]
                
                # ToBoxID 下拉選單
                to_box_index = st.selectbox(
                    "📥 目標容器 (ToBoxID)",
                    range(len(box_display_list)),
                    format_func=lambda x: box_display_list[x],
                    help="篩選特定目標容器的交易記錄",
                    key="to_box_select"
                )
                search_box_to = box_id_list[to_box_index]
                
                st.markdown("**📅 日期範圍**")
                date_range = st.date_input(
                    "選擇日期",
                    value=[],
                    help="選擇開始和結束日期（可選）",
                    label_visibility="collapsed"
                )
            
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                search_limit = st.slider("最大結果數", 10, 1000, 200, 10)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "🔍 執行查詢", 
                    type="primary", 
                    use_container_width=True
                )
        
        if submitted:
            # 獲取所有記錄
            transactions = TransactionLogOperations.get_transactions(limit=search_limit)
            
            if transactions:
                df = pd.DataFrame(transactions)
                
                # 應用篩選條件
                filtered_df = df.copy()
                
                # 篩選物料
                if search_item != "全部":
                    search_sn = search_item.split(" - ")[0]
                    filtered_df = filtered_df[filtered_df['SN'] == search_sn]
                
                # 篩選操作類型
                if search_action:
                    filtered_df = filtered_df[filtered_df['ActionType'].isin(search_action)]
                
                # 篩選操作人員
                if search_operator != "全部":
                    filtered_df = filtered_df[filtered_df['Operator'] == search_operator]
                
                # 篩選來源容器
                if search_box_from != "全部":
                    filtered_df = filtered_df[filtered_df['FromBoxID'] == search_box_from]
                
                # 篩選目標容器
                if search_box_to != "全部":
                    filtered_df = filtered_df[filtered_df['ToBoxID'] == search_box_to]
                
                # 篩選日期範圍
                if date_range and len(date_range) == 2:
                    if 'Timestamp' in filtered_df.columns:
                        filtered_df['Timestamp'] = pd.to_datetime(filtered_df['Timestamp'])
                        start_date = pd.Timestamp(date_range[0])
                        end_date = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
                        filtered_df = filtered_df[
                            (filtered_df['Timestamp'] >= start_date) & 
                            (filtered_df['Timestamp'] < end_date)
                        ]
                
                # 顯示結果
                if not filtered_df.empty:
                    st.success(f"🎯 找到 {len(filtered_df)} 筆符合條件的記錄")
                    
                    # 顯示篩選條件摘要
                    st.markdown("#### 📋 篩選條件摘要")
                    filter_summary = []
                    if search_item != "全部":
                        filter_summary.append(f"物料: {search_item}")
                    if search_action:
                        filter_summary.append(f"操作類型: {', '.join(search_action)}")
                    if search_operator != "全部":
                        filter_summary.append(f"操作人員: {search_operator}")
                    if search_box_from != "全部":
                        filter_summary.append(f"來源容器: {search_box_from}")
                    if search_box_to != "全部":
                        filter_summary.append(f"目標容器: {search_box_to}")
                    if date_range and len(date_range) == 2:
                        filter_summary.append(f"日期: {date_range[0]} ~ {date_range[1]}")
                    
                    if filter_summary:
                        st.info(" | ".join(filter_summary))
                    
                    # 顯示統計
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("查詢結果", len(filtered_df))
                    with col2:
                        if 'TransQty' in filtered_df.columns:
                            st.metric("總異動量", f"{filtered_df['TransQty'].sum():,}")
                    with col3:
                        if 'ActionType' in filtered_df.columns:
                            st.metric("操作類型", filtered_df['ActionType'].nunique())
                    with col4:
                        if 'StockAfter' in filtered_df.columns and 'StockBefore' in filtered_df.columns:
                            net_change = (filtered_df['StockAfter'] - filtered_df['StockBefore']).sum()
                            st.metric("淨變化", f"{net_change:+,}")
                    
                    st.markdown("---")
                    
                    # 顯示表格
                    st.dataframe(filtered_df, use_container_width=True, hide_index=True, height=400)
                    
                    # 匯出篩選結果
                    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 匯出查詢結果 (CSV)",
                        data=csv,
                        file_name=f"filtered_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("❌ 沒有找到符合條件的記錄，請調整篩選條件")
            else:
                st.warning("目前沒有交易記錄")
        else:
            st.info("👆 請設定篩選條件後點擊「執行查詢」按鈕")
    
    # ==================== Tab 4: 手動記錄 ====================
    with tab4:
        st.subheader("➕ 手動新增交易記錄")
        st.info("💡 建議使用「庫存異動」頁面進行標準操作，此處僅供特殊情況使用")
        
        # 獲取物料和容器列表
        items = ItemOperations.get_all_items(limit=500)
        boxes = MaterialOverviewOperations.get_all_boxes()
        
        if not items:
            st.warning("⚠️ 請先新增物料才能記錄交易")
            return
        
        item_options = [f"{item['SN']} - {item['ItemName']}" for item in items]
        box_options = ["0 - 外部/其他"] + [f"{box['BoxID']} - {box.get('Description', '')}" for box in boxes]
        
        with st.form("manual_transaction_form"):
            st.markdown("#### 📝 交易基本資訊")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_item = st.selectbox("選擇物料 *", item_options)
                action_type = st.selectbox(
                    "操作類型 *",
                    ['入庫', '出庫', '調撥', '報廢', '盤點', '退貨', '借出', '歸還']
                )
                trans_qty = st.number_input("異動數量 *", min_value=1, value=1)
            
            with col2:
                # 🎁 容器設定區塊 ⭐ 這就是您要的欄位！
                st.markdown("##### 🎁 容器設定")
                from_box = st.selectbox(
                    "📤 來源容器 (FromBoxID)", 
                    box_options, 
                    key="manual_from",
                    help="物料從哪個容器出來"
                )
                to_box = st.selectbox(
                    "📥 目標容器 (ToBoxID)", 
                    box_options, 
                    key="manual_to",
                    help="物料要放入哪個容器"
                )
                operator = st.text_input("操作人員 *", value="Admin")
            
            st.markdown("#### 📄 備註說明")
            remark = st.text_area(
                "備註",
                placeholder="請詳細說明此次交易的原因、目的或其他重要資訊",
                height=100
            )
            
            st.markdown("---")
            st.warning("⚠️ 此操作將直接修改庫存數量，請謹慎操作！")
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                submitted = st.form_submit_button(
                    "✅ 確認新增",
                    type="primary",
                    use_container_width=True
                )
        
        if submitted:
            sn = selected_item.split(" - ")[0]
            from_box_id = from_box.split(" - ")[0]
            to_box_id = to_box.split(" - ")[0]
            
            # 根據操作類型執行對應動作
            success = False
            
            if action_type == '入庫':
                success = TransactionLogOperations.stock_in(
                    sn, trans_qty, to_box_id, operator, remark
                )
            elif action_type == '出庫':
                success = TransactionLogOperations.stock_out(
                    sn, trans_qty, from_box_id, operator, remark
                )
            elif action_type == '調撥':
                success = TransactionLogOperations.transfer(
                    sn, trans_qty, from_box_id, to_box_id, operator, remark
                )
            else:
                # 其他類型使用通用方法
                trans_data = {
                    'SN': sn,
                    'ActionType': action_type,
                    'FromBoxID': from_box_id,
                    'ToBoxID': to_box_id,
                    'TransQty': trans_qty,
                    'Operator': operator,
                    'Remark': remark
                }
                success = TransactionLogOperations.add_transaction(trans_data)
            
            if success:
                st.session_state.message = {
                    'type': 'success',
                    'text': f'交易記錄新增成功！操作類型：{action_type}'
                }
                st.balloons()
                st.rerun()
            else:
                st.error(f"{ICONS['error']} 交易記錄新增失敗，請檢查資料或庫存是否足夠")

# ==================== 主程式 ====================
def main():
    """主程式"""
    render_sidebar()
    
    # 路由
    pages = {
        'dashboard': page_dashboard,
        'boxes': page_boxes,
        'items': page_items,
        'add_item': page_add_item,
        'stock_operations': page_stock_operations,
        'search': page_search,
        'transactions': page_transactions
    }
    
    page_func = pages.get(st.session_state.current_page, page_dashboard)
    page_func()

if __name__ ==