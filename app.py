"""
物料管理系統 - 三層架構完整版 (支援新版 TransactionLog + Locked 功能)
Tab1: 物料總覽表 (容器/專案管理) - CRUD + Lock/Unlock
Tab2: 物品明細清單 (物品管理) - 僅入庫功能
Tab3: 交易記錄 (僅調撥功能)
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 匯入資料庫操作
try:
    from data_operations import (
        MaterialOverviewOperations,
        ItemOperations,
        TransactionLogOperations
    )
    from db_config import DB_CONFIG
    DB_AVAILABLE = True
except ImportError as e:
    logger.error(f"無法導入資料庫模組: {e}")
    DB_AVAILABLE = False
    st.error("❌ 資料庫模組載入失敗")
    st.stop()

# ==================== 頁面配置 ====================
st.set_page_config(
    page_title="物料管理系統 - 三層架構",
    page_icon="📦",
    layout="wide"
)

# ==================== 樣式 ====================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
    }
    .locked-badge {
        background-color: #ff4444;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .unlocked-badge {
        background-color: #44ff44;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State ====================
if 'show_message' not in st.session_state:
    st.session_state.show_message = False
if 'message_type' not in st.session_state:
    st.session_state.message_type = 'info'
if 'message_text' not in st.session_state:
    st.session_state.message_text = ''

# ==================== 標題 ====================
st.markdown("""
<div class="main-header">
    <h1>📦 物料管理系統</h1>
    <p>容器管理 → 物品管理 → 交易記錄 (含鎖定功能)</p>
</div>
""", unsafe_allow_html=True)

# ==================== 訊息顯示 ====================
if st.session_state.show_message:
    if st.session_state.message_type == 'success':
        st.success(st.session_state.message_text)
    elif st.session_state.message_type == 'error':
        st.error(st.session_state.message_text)
    elif st.session_state.message_type == 'warning':
        st.warning(st.session_state.message_text)
    else:
        st.info(st.session_state.message_text)
    st.session_state.show_message = False

# ==================== 資料庫狀態與統計 ====================
col_status, col_refresh = st.columns([4, 1])

with col_status:
    try:
        stats = MaterialOverviewOperations.get_statistics()
        st.success(f"✅ 資料庫連接: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
    except Exception as e:
        st.error(f"❌ 資料庫錯誤: {e}")
        st.stop()

with col_refresh:
    if st.button("🔄 重新整理", width="stretch"):
        st.rerun()

# 統計卡片
st.markdown("### 📊 系統統計")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("📦 容器總數", stats.get('total_boxes', 0))
with col2:
    st.metric("🔒 鎖定容器", stats.get('locked_boxes', 0))
with col3:
    st.metric("📋 物品總數", stats.get('total_items', 0))
with col4:
    st.metric("📊 總庫存", f"{stats.get('total_quantity', 0):,}")
with col5:
    st.metric("⚠️ 低庫存", stats.get('low_stock_count', 0))
with col6:
    st.metric("🔴 零庫存", stats.get('zero_stock_count', 0))

st.markdown("---")

# ==================== 主要功能 Tab ====================
tab1, tab2, tab3 = st.tabs([
    "🗂️ 物料總覽表 (容器/專案)",
    "📋 物品明細清單 (僅入庫)",
    "📝 交易記錄 (僅調撥)"
])

# ==================== Tab 1: 容器管理 (新增 Lock 功能) ====================
with tab1:
    st.markdown("## 🗂️ 物料總覽表 - 容器/專案管理")
    
    subtab1, subtab2, subtab3 = st.tabs(["➕ 新增/查看", "✏️ 修改/刪除", "🔒 鎖定管理"])
    
    with subtab1:
        # 新增表單
        with st.form("add_box_form", clear_on_submit=True):
            st.subheader("➕ 新增容器")
            col1, col2 = st.columns(2)
            with col1:
                box_id = st.text_input("容器ID *", placeholder="BOX-001")
                category = st.text_input("分類", placeholder="電子零件")
            with col2:
                owner = st.text_input("負責人", placeholder="張三")
                status = st.selectbox("狀態", ["使用中", "閒置", "結案"])
            
            description = st.text_area("描述", placeholder="容器說明...")
            
            if st.form_submit_button("💾 新增容器", type="primary"):
                if box_id:
                    if MaterialOverviewOperations.add_box({
                        'BoxID': box_id, 'Category': category,
                        'Description': description, 'Owner': owner, 'Status': status
                    }):
                        st.success(f"✅ 容器「{box_id}」新增成功!")
                        st.rerun()
                    else:
                        st.error("❌ 新增失敗 (可能重複)")
                else:
                    st.error("❌ 請填寫容器ID")
        
        st.markdown("---")
        
        # 查看容器 (顯示鎖定狀態)
        st.subheader("🔍 所有容器")
        
        # 篩選選項
        col_filter1, col_filter2 = st.columns([1, 3])
        with col_filter1:
            show_locked = st.checkbox("顯示已鎖定", value=True)
        
        boxes = MaterialOverviewOperations.get_all_boxes()
        if boxes:
            df_boxes = pd.DataFrame(boxes)
            
            # 添加鎖定狀態顯示
            if 'Locked' in df_boxes.columns:
                df_boxes['鎖定狀態'] = df_boxes['Locked'].apply(
                    lambda x: '🔒 已鎖定' if x == 1 else '🔓 未鎖定'
                )
            
            st.dataframe(
                df_boxes, 
                width="stretch", 
                hide_index=True, 
                height=300,
                column_config={
                    "BoxID": "容器ID",
                    "Category": "分類",
                    "Description": "描述",
                    "Owner": "負責人",
                    "Status": "狀態",
                    "Locked": st.column_config.CheckboxColumn("鎖定"),
                    "鎖定狀態": "鎖定狀態",
                    "CreateDate": st.column_config.DatetimeColumn("建立時間", format="YYYY-MM-DD HH:mm")
                }
            )
        else:
            st.info("目前沒有容器")
    
    with subtab2:
        boxes_edit = MaterialOverviewOperations.get_all_boxes()
        if boxes_edit:
            selected_box = st.selectbox(
                "選擇容器",
                options=[b['BoxID'] for b in boxes_edit],
                format_func=lambda x: f"{x} - {next((b['Description'] or '無描述' for b in boxes_edit if b['BoxID']==x), '')} {'🔒' if next((b.get('Locked', 0) for b in boxes_edit if b['BoxID']==x), 0) == 1 else ''}"
            )
            
            box = next((b for b in boxes_edit if b['BoxID'] == selected_box), None)
            
            if box:
                # 顯示鎖定狀態警告
                is_locked = box.get('Locked', 0) == 1
                if is_locked:
                    st.error("🔒 此容器已鎖定，無法修改或刪除！請先到「鎖定管理」解鎖。")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**修改資訊**")
                    new_category = st.text_input("分類", value=box['Category'] or '', disabled=is_locked)
                    new_owner = st.text_input("負責人", value=box['Owner'] or '', disabled=is_locked)
                    
                    # 狀態選項
                    status_options = ["使用中", "閒置", "結案"]
                    current_status = box.get('Status', '使用中')
                    
                    # 處理可能的狀態值變體
                    status_mapping = {
                        '使用中': '使用中',
                        '閒置': '閒置',
                        '空閒': '閒置',  # 舊版本相容
                        '結案': '結案',
                        '歸檔': '結案'   # 舊版本相容
                    }
                    
                    # 轉換為標準狀態
                    normalized_status = status_mapping.get(current_status, '使用中')
                    
                    try:
                        status_index = status_options.index(normalized_status)
                    except ValueError:
                        status_index = 0  # 預設為「使用中」
                    
                    new_status = st.selectbox(
                        "狀態", 
                        status_options, 
                        index=status_index,
                        disabled=is_locked
                    )
                    new_desc = st.text_area("描述", value=box['Description'] or '', disabled=is_locked)
                    
                    if st.button("💾 更新容器", type="primary", disabled=is_locked):
                        if MaterialOverviewOperations.update_box(selected_box, {
                            'Category': new_category, 'Owner': new_owner,
                            'Status': new_status, 'Description': new_desc
                        }):
                            st.success("✅ 更新成功!")
                            st.rerun()
                        else:
                            st.error("❌ 更新失敗 (容器可能已鎖定)")
                
                with col2:
                    st.write("**刪除容器**")
                    if is_locked:
                        st.warning("🔒 已鎖定，無法刪除")
                    else:
                        st.warning("⚠️ 只能刪除沒有物品的容器")
                        items_count = len(ItemOperations.get_items_by_box(selected_box))
                        st.metric("物品數量", items_count)
                        
                        if items_count == 0:
                            if st.button("🗑️ 刪除容器", type="secondary"):
                                if MaterialOverviewOperations.delete_box(selected_box):
                                    st.success("✅ 刪除成功!")
                                    st.rerun()
                                else:
                                    st.error("❌ 刪除失敗")
                        else:
                            st.error(f"❌ 此容器還有 {items_count} 個物品")
        else:
            st.info("目前沒有容器")
    
    with subtab3:
        st.subheader("🔒 容器鎖定管理")
        st.info("💡 鎖定容器後將無法進行任何修改、新增或刪除操作，適用於結案專案")
        
        boxes_lock = MaterialOverviewOperations.get_all_boxes()
        if boxes_lock:
            # 分類顯示
            col_unlock, col_lock = st.columns(2)
            
            with col_unlock:
                st.markdown("### 🔓 未鎖定容器")
                unlocked = [b for b in boxes_lock if b.get('Locked', 0) == 0]
                
                if unlocked:
                    for box in unlocked:
                        with st.container():
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                st.write(f"**{box['BoxID']}**")
                                st.caption(f"分類: {box.get('Category', 'N/A')} | 狀態: {box.get('Status', 'N/A')}")
                                st.caption(f"描述: {box.get('Description', '無')}")
                            with col_btn:
                                if st.button(f"🔒 鎖定", key=f"lock_{box['BoxID']}"):
                                    if MaterialOverviewOperations.lock_box(box['BoxID']):
                                        st.session_state.show_message = True
                                        st.session_state.message_type = 'success'
                                        st.session_state.message_text = f"✅ 容器 {box['BoxID']} 已鎖定"
                                        st.rerun()
                                    else:
                                        st.error("❌ 鎖定失敗")
                            st.markdown("---")
                else:
                    st.info("所有容器都已鎖定")
            
            with col_lock:
                st.markdown("### 🔒 已鎖定容器")
                locked = [b for b in boxes_lock if b.get('Locked', 0) == 1]
                
                if locked:
                    for box in locked:
                        with st.container():
                            col_info, col_btn = st.columns([3, 1])
                            with col_info:
                                st.write(f"**{box['BoxID']}** 🔒")
                                st.caption(f"分類: {box.get('Category', 'N/A')} | 狀態: {box.get('Status', 'N/A')}")
                                st.caption(f"描述: {box.get('Description', '無')}")
                            with col_btn:
                                if st.button(f"🔓 解鎖", key=f"unlock_{box['BoxID']}", type="secondary"):
                                    if MaterialOverviewOperations.unlock_box(box['BoxID']):
                                        st.session_state.show_message = True
                                        st.session_state.message_type = 'success'
                                        st.session_state.message_text = f"✅ 容器 {box['BoxID']} 已解鎖"
                                        st.rerun()
                                    else:
                                        st.error("❌ 解鎖失敗")
                            st.markdown("---")
                else:
                    st.info("目前沒有鎖定的容器")
        else:
            st.info("目前沒有容器")

# ==================== Tab 2: 物品管理 (物品入庫) ====================
with tab2:
    st.markdown("## 📋 物品明細清單 - 物品入庫")
    st.info("💡 請輸入物品資訊進行入庫，系統會自動產生物品編號(SN)")
    
    subtab1, subtab2 = st.tabs(["📥 物品入庫", "🔍 查看物品"])
    
    with subtab1:
        st.subheader("📥 新增物品入庫")
        
        # 獲取所有容器（未鎖定）
        all_boxes_data = MaterialOverviewOperations.get_all_boxes()
        
        if all_boxes_data:
            with st.form("add_item_form", clear_on_submit=True):
                st.markdown("### 📝 物品基本資訊")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    item_name = st.text_input(
                        "物品名稱 *",
                        placeholder="例：電阻器",
                        help="必填欄位"
                    )
                    spec = st.text_input(
                        "規格",
                        placeholder="例：10kΩ ±5%",
                        help="物品規格說明"
                    )
                    location = st.text_input(
                        "存放位置",
                        placeholder="例：倉庫A-架位3",
                        help="物理存放位置"
                    )
                
                with col2:
                    # BoxID 下拉選單
                    box_options = [f"{b['BoxID']} - {b.get('Description', '')}" for b in all_boxes_data]
                    box_selection = st.selectbox(
                        "容器 (BoxID) *",
                        options=box_options,
                        help="選擇要存放的容器"
                    )
                    box_id = box_selection.split(" - ")[0]
                    
                    quantity = st.number_input(
                        "入庫數量 *",
                        min_value=0,
                        value=1,
                        help="初始庫存數量"
                    )
                    
                    operator = st.text_input(
                        "操作人員",
                        value="Admin",
                        help="執行入庫的人員"
                    )
                
                st.markdown("### 📄 備註說明")
                remark = st.text_area(
                    "備註",
                    placeholder="請說明此次入庫的原因、來源或其他重要資訊...",
                    height=100
                )
                
                st.markdown("---")
                
                # 預覽資訊
                with st.expander("📋 預覽入庫資訊", expanded=False):
                    preview_col1, preview_col2 = st.columns(2)
                    with preview_col1:
                        st.write("**物品資訊**")
                        st.write(f"• 物品名稱: {item_name or '(未填寫)'}")
                        st.write(f"• 規格: {spec or '(未填寫)'}")
                        st.write(f"• 位置: {location or '(未填寫)'}")
                    with preview_col2:
                        st.write("**入庫資訊**")
                        st.write(f"• 容器: {box_id}")
                        st.write(f"• 數量: {quantity}")
                        st.write(f"• 操作人員: {operator}")
                
                col_btn1, col_btn2 = st.columns([1, 3])
                with col_btn1:
                    submit = st.form_submit_button("✅ 確認入庫", type="primary", width="stretch")
                
                if submit:
                    # 驗證必填欄位
                    if not item_name:
                        st.error("❌ 請填寫物品名稱")
                    elif not box_id:
                        st.error("❌ 請選擇容器")
                    else:
                        # 準備物品資料
                        item_data = {
                            'ItemName': item_name,
                            'Spec': spec,
                            'Location': location,
                            'BoxID': box_id,
                            'Quantity': quantity
                        }
                        
                        # 新增物品
                        success = ItemOperations.add_item(item_data, check_locked=True)
                        
                        if success:
                            st.session_state.show_message = True
                            st.session_state.message_type = 'success'
                            st.session_state.message_text = f"✅ 物品「{item_name}」入庫成功！數量: {quantity}，容器: {box_id}"
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ 入庫失敗，請檢查容器是否已鎖定或資料是否正確")
        else:
            st.warning("📭 目前沒有可用容器（未鎖定），請先到 Tab1 新增容器或解鎖現有容器")
    
    with subtab2:
        st.subheader("🔍 查看所有物品")
        
        items = ItemOperations.get_all_items(limit=1000)
        
        if items:
            df_items = pd.DataFrame(items)
            
            # 統計資訊
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("物品總數", len(df_items))
            with col2:
                total_qty = df_items['Quantity'].sum() if 'Quantity' in df_items.columns else 0
                st.metric("總庫存", f"{total_qty:,}")
            with col3:
                low_stock = len(df_items[df_items['Quantity'] < 10]) if 'Quantity' in df_items.columns else 0
                st.metric("低庫存 (<10)", low_stock)
            with col4:
                zero_stock = len(df_items[df_items['Quantity'] == 0]) if 'Quantity' in df_items.columns else 0
                st.metric("零庫存", zero_stock)
            
            st.markdown("---")
            
            st.dataframe(
                df_items,
                width="stretch",
                hide_index=True,
                height=400,
                column_config={
                    "SN": "物品編號",
                    "ItemName": "物品名稱",
                    "Spec": "規格",
                    "Location": "位置",
                    "BoxID": "容器ID",
                    "Quantity": st.column_config.NumberColumn("數量", format="%d"),
                    "UpdateTime": st.column_config.DatetimeColumn("更新時間", format="YYYY-MM-DD HH:mm")
                }
            )
            
            # 匯出
            csv = df_items.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 匯出 CSV",
                data=csv,
                file_name=f"items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 目前沒有物品")

# ==================== Tab 3: 交易記錄 (僅調撥功能) ====================
with tab3:
    st.markdown("## 📝 交易記錄 - 僅支援調撥操作")
    st.info("💡 此頁面僅提供調撥功能，入庫操作請至「物品明細清單」頁籤")
    
    subtab1, subtab2 = st.tabs(["🔄 調撥操作", "📊 查看記錄"])
    
    with subtab1:
        st.subheader("🔄 物品調撥")
        
        # 獲取所有物品和容器
        all_items = ItemOperations.get_all_items(limit=500)
        # 獲取所有容器（包含鎖定的）用於篩選顯示
        all_boxes_for_filter = MaterialOverviewOperations.get_all_boxes()
        # 獲取未鎖定的容器用於調撥操作
        all_boxes_data = MaterialOverviewOperations.get_all_boxes()
        
        if all_boxes_for_filter:
            # 容器篩選器（在表單外）- 使用物料總覽表的所有 BoxID
            st.markdown("### 🎁 容器篩選")
            col_filter1, col_filter2 = st.columns([2, 3])
            
            with col_filter1:
                # 從物料總覽表獲取所有容器，包含鎖定的容器
                box_filter_options = ["全部容器"] + [
                    f"{b['BoxID']} - {b.get('Description', '')} {'🔒' if b.get('Locked', 0) == 1 else ''}" 
                    for b in all_boxes_for_filter
                ]
                selected_box_filter = st.selectbox(
                    "選擇容器查看物品",
                    options=box_filter_options,
                    help="篩選特定容器內的物品（顯示所有容器，包含已鎖定）"
                )
            
            # 根據選擇的容器篩選物品
            if selected_box_filter == "全部容器":
                filtered_items = all_items if all_items else []
                st.info(f"📦 顯示所有容器的物品 (共 {len(filtered_items)} 項)")
            else:
                # 提取 BoxID（移除描述和鎖定圖示）
                selected_box_id = selected_box_filter.split(" - ")[0].strip()
                filtered_items = [item for item in all_items if item.get('BoxID') == selected_box_id] if all_items else []
                
                # 檢查該容器是否鎖定
                selected_box = next((b for b in all_boxes_for_filter if b['BoxID'] == selected_box_id), None)
                is_box_locked = selected_box.get('Locked', 0) == 1 if selected_box else False
                
                if is_box_locked:
                    st.warning(f"🔒 容器「{selected_box_filter}」已鎖定，無法進行調撥操作")
                st.info(f"📦 容器「{selected_box_filter}」內的物品 (共 {len(filtered_items)} 項)")
            
            st.markdown("---")
            
            if filtered_items and all_boxes_data:
                with st.form("transfer_form"):
                    st.markdown("### 📝 調撥資訊")
                    
                    # 預先定義 box_id_options（用於多個地方）
                    box_id_options = [f"{b['BoxID']} - {b.get('Description', '')}" for b in all_boxes_data]
                    
                    # 第一列：物品、BoxID、數量、操作員
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        item_options = [f"{item['SN']} - {item['ItemName']}" for item in filtered_items]
                        selected_item_str = st.selectbox("選擇物品 *", item_options)
                        selected_sn = selected_item_str.split(" - ")[0]
                        item = next((i for i in filtered_items if i['SN'] == selected_sn), None)
                    
                    with col2:
                        # 如果有物品，預設選擇該物品所在的容器
                        if item:
                            current_box_str = f"{item['BoxID']} - "
                            box_id_default = next((i for i, opt in enumerate(box_id_options) if opt.startswith(current_box_str)), 0)
                        else:
                            box_id_default = 0
                        
                        selected_boxid = st.selectbox(
                            "當前容器 (BoxID) *",
                            options=box_id_options,
                            index=box_id_default,
                            help="物品當前所在容器"
                        )
                    
                    with col3:
                        qty = st.number_input("調撥數量", min_value=1, value=1)
                    
                    with col4:
                        operator = st.text_input("操作員", value="Admin")
                    
                    # 第二列：來源容器、目標容器
                    st.markdown("---")
                    col_from, col_to = st.columns(2)
                    
                    with col_from:
                        # 來源容器改為不可編輯的顯示（使用 disabled 參數）
                        current_box_str = f"{item['BoxID']} - " if item else ""
                        from_default = next((i for i, opt in enumerate(box_id_options) if opt.startswith(current_box_str)), 0)
                        
                        from_box_selection = st.selectbox(
                            "📤 來源容器 (FromBoxID) *",
                            options=box_id_options,
                            index=from_default,
                            help="物料從哪個容器出來（自動帶入，不可修改）",
                            disabled=True,  # 設為不可編輯
                            key="from_box_disabled"
                        )
                    
                    with col_to:
                        to_box_selection = st.selectbox(
                            "📥 目標容器 (ToBoxID) *",
                            options=box_id_options,
                            index=0,
                            help="物料要放入哪個容器",
                            key="to_box_selection"
                        )
                    
                    from_box_id = from_box_selection.split(" - ")[0]
                    to_box_id = to_box_selection.split(" - ")[0]
                    
                    # 驗證
                    validation_error = None
                    if from_box_id == to_box_id:
                        validation_error = "❌ 調撥時來源容器和目標容器不能相同！"
                        st.error(validation_error)
                    
                    # 物品資訊顯示
                    if item:
                        st.markdown("---")
                        st.markdown("### 📊 物品資訊")
                        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                        with col_info1:
                            st.metric("當前庫存", item.get('Quantity', 0))
                        with col_info2:
                            st.metric("當前容器", item.get('BoxID', 'N/A'))
                        with col_info3:
                            st.metric("規格", item.get('Spec', 'N/A'))
                        with col_info4:
                            st.metric("位置", item.get('Location', 'N/A'))
                    
                    st.markdown("---")
                    st.markdown("### 📄 備註說明")
                    remark = st.text_area(
                        "備註",
                        placeholder="請說明調撥原因...",
                        height=80,
                        key="remark_input"
                    )
                    
                    st.markdown("---")
                    
                    # 即時預覽調撥資訊（改為始終展開的資訊卡片）
                    st.markdown("### 📋 預覽調撥資訊")
                    
                    # 計算調撥後的庫存
                    current_qty = item.get('Quantity', 0) if item else 0
                    after_qty = current_qty - qty
                    
                    # 檢查庫存是否足夠
                    stock_warning = ""
                    if after_qty < 0:
                        stock_warning = "⚠️ 庫存不足！"
                    elif after_qty == 0:
                        stock_warning = "⚠️ 調撥後將為零庫存"
                    elif after_qty < 10:
                        stock_warning = "⚠️ 調撥後為低庫存"
                    
                    # 使用容器顯示預覽資訊
                    preview_container = st.container()
                    with preview_container:
                        # 第一列：基本資訊
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            st.markdown(f"""
                            **📦 物品資訊**
                            - 物品名稱: `{item['ItemName'] if item else 'N/A'}`
                            - 物品編號: `{item['SN'] if item else 'N/A'}`
                            - 規格: `{item.get('Spec', '無') if item else 'N/A'}`
                            """)
                        with col_p2:
                            st.markdown(f"""
                            **📊 數量資訊**
                            - 當前庫存: `{current_qty}`
                            - 調撥數量: `{qty}`
                            - 調撥後庫存: `{after_qty}` {stock_warning}
                            """)
                        
                        # 第二列：調撥路徑
                        st.markdown("**🔄 調撥路徑**")
                        col_p3, col_p4, col_p5 = st.columns([2, 1, 2])
                        with col_p3:
                            st.info(f"📤 來源: {from_box_selection}")
                        with col_p4:
                            st.markdown("<div style='text-align: center; padding-top: 0.5rem;'>→</div>", unsafe_allow_html=True)
                        with col_p5:
                            st.success(f"📥 目標: {to_box_selection}")
                        
                        # 第三列：操作資訊
                        col_p6, col_p7 = st.columns(2)
                        with col_p6:
                            st.markdown(f"**👤 操作人員**: `{operator}`")
                        with col_p7:
                            st.markdown(f"**📝 備註**: `{remark if remark else '(無)'}`")
                        
                        # 驗證狀態
                        if validation_error:
                            st.error(validation_error)
                        elif after_qty < 0:
                            st.error(f"❌ 庫存不足！當前庫存 {current_qty}，無法調出 {qty}")
                        else:
                            st.success("✅ 調撥資訊驗證通過，可以執行調撥")
                    
                    st.markdown("---")
                    
                    col_btn1, col_btn2 = st.columns([1, 3])
                    with col_btn1:
                        submit = st.form_submit_button("✅ 執行調撥", type="primary", width="stretch")
                    
                    if submit:
                        if from_box_id == to_box_id:
                            st.error("❌ 調撥時來源容器和目標容器不能相同！")
                        else:
                            success = TransactionLogOperations.transfer(
                                sn=item['SN'],
                                quantity=qty,
                                from_box_id=from_box_id,
                                to_box_id=to_box_id,
                                operator=operator,
                                remark=remark
                            )
                            
                            if success:
                                st.session_state.show_message = True
                                st.session_state.message_type = 'success'
                                st.session_state.message_text = f"✅ 調撥成功！「{item['ItemName']}」從 {from_box_selection} 至 {to_box_selection}"
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ 調撥失敗，請檢查庫存是否足夠")
            else:
                st.warning(f"📭 所選容器內沒有物品")
        else:
            if not all_boxes_for_filter:
                st.warning("📭 目前沒有容器，請先到 Tab1 新增容器")
            elif not all_items:
                st.warning("📭 目前沒有物品，請先到 Tab2 新增物品")
            elif not all_boxes_data:
                st.warning("📭 目前沒有可用容器（未鎖定），無法進行調撥操作")
    
    with subtab2:
        st.subheader("📊 查看交易記錄")
        
        limit = st.slider("顯示筆數", 10, 500, 100, 10)
        
        transactions = TransactionLogOperations.get_transactions(limit=limit)
        
        if transactions:
            df_trans = pd.DataFrame(transactions)
            
            # 統計
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("總記錄", len(transactions))
            with col2:
                st.metric("操作類型", df_trans['ActionType'].nunique() if 'ActionType' in df_trans.columns else 0)
            with col3:
                st.metric("操作人員", df_trans['Operator'].nunique() if 'Operator' in df_trans.columns else 0)
            with col4:
                total_qty = abs(df_trans['TransQty'].sum()) if 'TransQty' in df_trans.columns else 0
                st.metric("總異動量", f"{total_qty:,}")
            
            st.markdown("---")
            
            # 顯示記錄
            st.dataframe(
                df_trans,
                width="stretch",
                hide_index=True,
                height=400,
                column_config={
                    "LogID": "記錄ID",
                    "SN": "物品SN",
                    "ActionType": "操作",
                    "FromBoxID": "來源容器",
                    "ToBoxID": "目的容器",
                    "TransQty": "數量",
                    "StockBefore": "操作前庫存",
                    "StockAfter": "操作後庫存",
                    "Operator": "操作員",
                    "Remark": "備註",
                    "Timestamp": st.column_config.DatetimeColumn("交易時間", format="YYYY-MM-DD HH:mm:ss")
                }
            )
            
            # 匯出
            csv = df_trans.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 匯出 CSV",
                data=csv,
                file_name=f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 目前沒有交易記錄")

# ==================== 側邊欄 ====================
with st.sidebar:
    st.markdown("### ⚙️ 系統資訊")
    st.markdown(f"""
    **資料庫**
    - 主機: `{DB_CONFIG['host']}`
    - 資料庫: `{DB_CONFIG['database']}`
    - 狀態: ✅ 已連接
    """)
    
    st.markdown("---")
    st.markdown("### 📊 快速統計")
    st.metric("容器數", f"{stats.get('total_boxes', 0):,}")
    st.metric("🔒 鎖定", f"{stats.get('locked_boxes', 0):,}")
    st.metric("物品數", f"{stats.get('total_items', 0):,}")
    st.metric("總庫存", f"{stats.get('total_quantity', 0):,}")
    
    if stats.get('low_stock_count', 0) > 0:
        st.warning(f"⚠️ {stats['low_stock_count']} 項低庫存")
    if stats.get('zero_stock_count', 0) > 0:
        st.error(f"🔴 {stats['zero_stock_count']} 項零庫存")
    
    st.markdown("---")
    st.markdown("### 📋 功能說明")
    st.markdown("""
    **Tab1 - 物料總覽**
    - 容器 CRUD 操作
    - 🔒 鎖定/解鎖管理
    
    **Tab2 - 物品明細**
    - 📥 僅入庫功能
    
    **Tab3 - 交易記錄**
    - 🔄 僅調撥功能
    """)
    
    st.markdown("---")
    st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("版本: v5.0 - Locked + 簡化功能")