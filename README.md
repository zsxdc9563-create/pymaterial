# Material Management System

## 專案介紹
本系統為一套以 Box 為核心的物料管理系統，
可進行物料管理、庫存控制與交易紀錄追蹤。

## 功能
- 建立 Box 容器
- 新增物料
- 出庫管理
- 自動產生交易紀錄

## API

### 建立 Box
POST /api/boxes/

### 新增物料
POST /api/materials/

### 出庫
POST /api/materials/out/

### 查交易紀錄
GET /api/transactions/

## 系統流程
新增物料 → 自動寫入 TransactionLog  
出庫 → 扣庫存 → 寫入 TransactionLog