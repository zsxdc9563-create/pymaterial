# 物料管理系統 MMS（Material Management System）

> 自主開發的全端 Web 應用程式，作為後端工程師求職作品集。  
> 從需求分析、資料庫設計到前後端實作，獨立完成。

---

## 專案背景

此系統源自實習期間觀察到的實際痛點：公司物料分散管理、缺乏統一識別、無法追蹤異動歷史。

提出並設計這套系統，核心理念是以 **BoxID（容器編號）** 作為唯一識別符，所有物料都掛載在容器底下，讓庫存流向清晰可追蹤。

---

## 技術架構

```
前端（Django Template + Bootstrap 5）
        ↕
後端（Django Views + Service Layer）
        ↕
資料庫（PostgreSQL 17）
```

| 類別 | 技術選擇 | 選擇原因 |
|------|---------|---------|
| 後端框架 | Django 5.x | 快速開發、ORM 成熟、內建 Admin |
| API 層 | Django REST Framework | 為未來 React 前端預留擴充空間 |
| 資料庫 | PostgreSQL 17 | 支援 ACID、適合庫存交易場景 |
| 前端 | Django Template + Bootstrap 5 | 快速迭代，不需額外建置前端環境 |

---

## 系統設計亮點

### 1. Service Layer 架構
將業務邏輯從 View 中抽離，分為 `box_service`、`material_service`、`bom_service`、`transaction_service`，提高可測試性與維護性。

```
Views（HTTP 處理）→ Service（業務邏輯）→ Models（資料存取）
```

### 2. BoxID 核心設計
所有物料都必須掛載在容器底下，避免孤兒資料，確保庫存可追蹤。

```
BoxID（容器）
  └── MaterialItems（物料）
        └── TransactionLog（異動記錄）
```

### 3. 樂觀鎖定機制
使用 `select_for_update()` + `@transaction.atomic` 防止並發操作導致庫存計算錯誤。

### 4. 三層角色權限
```
Admin   → 全部功能
Manager → 新增/編輯/入出庫（個人容器限 owner 編輯）
Employee → 查看 + 入出庫
```

### 5. BOM 到料追蹤
專案容器支援設定物料需求量，系統自動計算缺料數與到料進度，支援批次領料扣庫存。

---

## 功能模組

| 模組 | 功能說明 |
|------|---------|
| 容器管理 | 新增/編輯/刪除/鎖定容器，支援 Tab 切換類型 |
| 物料管理 | 入庫/出庫/盤點調整，異動自動寫入交易記錄 |
| BOM 管理 | 設定需求量、追蹤到料進度、批次領料 |
| 物品調撥 | 跨容器移動物料，自動記錄來源與目的地 |
| 交易記錄 | 完整異動歷史，支援依容器篩選 |
| 權限控制 | Django Group 三層角色 + 箱子層級 owner 控制 |
| Excel 匯入/匯出 | 支援批次建立容器資料 |

---

## 資料模型設計

```
MaterialOverview（容器）
├── box_id          PK, VARCHAR
├── box_type        ENUM (project/personal/warehouse/spare/other)
├── owner           FK → User
├── is_locked       BOOLEAN
└── created_at      DATETIME

MaterialItems（物料）
├── sn              料號
├── item_name       品名
├── quantity        庫存數量
├── required_qty    BOM 需求量（NULL 表示非 BOM 項目）
└── box             FK → MaterialOverview

TransactionLog（交易記錄）
├── action_type     ENUM (IN/OUT/MOVE/ADJUST/BORROW/RETURN)
├── from_box_id     來源箱快照
├── to_box_id       目的箱快照
├── trans_qty       異動數量
├── stock_before    異動前庫存
└── operator        FK → User
```

---

## 安裝與執行

```bash
# 1. 克隆專案
git clone https://github.com/你的帳號/pymaterial.git
cd pymaterial

# 2. 建立虛擬環境
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定資料庫（PostgreSQL）
# 建立資料庫 pymaterial，並在 settings.py 設定連線資訊

# 5. 執行 Migration
python manage.py migrate

# 6. 建立測試帳號
python manage.py createsuperuser

# 7. 啟動伺服器
python manage.py runserver
```

開啟 `http://127.0.0.1:8000/material/`

---

## 學習歷程與反思

這個專案是我從 **零開始自學 Django** 的成果。

**遇到的挑戰：**
- 從 SQLite 遷移到 PostgreSQL，理解資料庫連線與 Migration 機制
- 設計 Service Layer 時，學習如何正確使用 `select_for_update` 防止競態條件
- 理解 Django 的三層認證架構（User → Group → Permission）並實作 RBAC

**未來規劃：**
- 前端改用 React + DRF API（後端 API 已預先設計完成）
- 加入 JWT 認證取代 Session Auth
- Docker 容器化部署

---

## 關於我

**陳靜婕（Sabrina Chen）**

曾任 SCADA/HMI 工程師一年，對工業通訊協定（Modbus RTU、RS-485）有實務接觸，
理解工廠自動化與設備監控的運作流程。

目前轉職專注於 **Python 後端開發**。

**學習歷程：**

自學 Python 與 Django 基礎後，在實習期間第一次參與真實專案開發。
面對實際需求與問題，在主管與同事的指導下，邊做邊學逐步建立系統架構思維、
資料庫設計與前後端整合能力，從零實作經驗成長到能夠獨立完成功能模組。

**實作專案：**

- 📦 **物料管理系統（本專案）**：實習期間在主管與同事指導下參與開發，
  負責系統架構設計、Django 後端、PostgreSQL 資料庫設計與前端模板實作

**技術能力：**  
Python / Django / Django REST Framework / PostgreSQL / LINE Bot API / Modbus RTU

目前積極尋找 **Python 後端工程師** 職位。

🔗 GitHub：https://github.com/zsxdc9563-create
📧 zsxdc9563@gmail.com