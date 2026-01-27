# data_operations.py (支援帶空格的資料表名稱)
"""
資料庫操作層 - 支援帶空格的資料表名稱
- `Material Overview` 
- `Item List`
- `TransactionLog`
"""
import logging
from datetime import datetime
import uuid
import db_config

logger = logging.getLogger(__name__)

# ==================== 1. 容器/專案管理操作 ====================
class MaterialOverviewOperations:
    """物料總覽表操作"""
    
    @staticmethod
    def get_all_boxes():
        try:
            query = """
                SELECT BoxID, Category, Description, Owner, Status, Locked, CreateDate
                FROM `Material Overview`
                ORDER BY CreateDate DESC
            """
            return db_config.execute_query(query)
        except Exception as e:
            logger.error(f"取得容器列表失敗: {e}")
            return []
    
    @staticmethod
    def get_box_by_id(box_id):
        try:
            query = """
                SELECT BoxID, Category, Description, Owner, Status, Locked, CreateDate
                FROM `Material Overview`
                WHERE BoxID = %s
            """
            result = db_config.execute_query(query, (box_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"取得容器失敗: {e}")
            return None
    
    @staticmethod
    def add_box(box_data):
        try:
            query = """
                INSERT INTO `Material Overview` (BoxID, Category, Description, Owner, Status, Locked)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                box_data.get('BoxID'),
                box_data.get('Category', ''),
                box_data.get('Description', ''),
                box_data.get('Owner', ''),
                box_data.get('Status', '使用中'),
                box_data.get('Locked', 0)
            )
            affected = db_config.execute_update(query, params)
            logger.info(f"✅ 新增容器: {box_data.get('BoxID')}")
            return affected > 0
        except Exception as e:
            logger.error(f"新增容器失敗: {e}")
            return False
    
    @staticmethod
    def update_box(box_id, box_data):
        try:
            query = """
                UPDATE `Material Overview`
                SET Category = %s, Description = %s, Owner = %s, Status = %s, Locked = %s
                WHERE BoxID = %s
            """
            params = (
                box_data.get('Category', ''),
                box_data.get('Description', ''),
                box_data.get('Owner', ''),
                box_data.get('Status', '使用中'),
                box_data.get('Locked', 0),
                box_id
            )
            affected = db_config.execute_update(query, params)
            return affected > 0
        except Exception as e:
            logger.error(f"更新容器失敗: {e}")
            return False
    
    @staticmethod
    def delete_box(box_id):
        try:
            check_query = "SELECT COUNT(*) as count FROM `Item List` WHERE BoxID = %s"
            result = db_config.execute_query(check_query, (box_id,))
            if result and result[0]['count'] > 0:
                logger.warning(f"容器 {box_id} 還有物品，無法刪除")
                return False
            
            query = "DELETE FROM `Material Overview` WHERE BoxID = %s"
            affected = db_config.execute_update(query, (box_id,))
            return affected > 0
        except Exception as e:
            logger.error(f"刪除容器失敗: {e}")
            return False
    
    @staticmethod
    def get_statistics():
        try:
            stats = {}
            
            query1 = "SELECT COUNT(*) as count FROM `Material Overview`"
            result1 = db_config.execute_query(query1)
            stats['total_boxes'] = result1[0]['count'] if result1 else 0
            
            query2 = "SELECT COUNT(*) as count FROM `Item List`"
            result2 = db_config.execute_query(query2)
            stats['total_items'] = result2[0]['count'] if result2 else 0
            
            query3 = "SELECT SUM(Quantity) as total FROM `Item List`"
            result3 = db_config.execute_query(query3)
            stats['total_quantity'] = result3[0]['total'] if result3 and result3[0]['total'] else 0
            
            query4 = "SELECT COUNT(*) as count FROM `Item List` WHERE Quantity > 0 AND Quantity < 10"
            result4 = db_config.execute_query(query4)
            stats['low_stock_count'] = result4[0]['count'] if result4 else 0
            
            query5 = "SELECT COUNT(*) as count FROM `Item List` WHERE Quantity = 0"
            result5 = db_config.execute_query(query5)
            stats['zero_stock_count'] = result5[0]['count'] if result5 else 0
            
            return stats
        except Exception as e:
            logger.error(f"取得統計資訊失敗: {e}")
            return {'total_boxes': 0, 'total_items': 0, 'total_quantity': 0, 'low_stock_count': 0, 'zero_stock_count': 0}

# ==================== 2. 物品管理操作 ====================
class ItemOperations:
    """物品明細清單操作"""
    
    @staticmethod
    def get_all_items(limit=500):
        try:
            query = """
                SELECT SN, ItemName, Spec, Location, BoxID, Quantity, UpdateTime
                FROM `Item List`
                ORDER BY UpdateTime DESC
                LIMIT %s
            """
            return db_config.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"取得物品列表失敗: {e}")
            return []
    
    @staticmethod
    def get_items_by_box(box_id):
        try:
            query = """
                SELECT SN, ItemName, Spec, Location, BoxID, Quantity, UpdateTime
                FROM `Item List`
                WHERE BoxID = %s
                ORDER BY ItemName
            """
            return db_config.execute_query(query, (box_id,))
        except Exception as e:
            logger.error(f"取得容器物品失敗: {e}")
            return []
    
    @staticmethod
    def get_item_by_sn(sn):
        try:
            query = """
                SELECT SN, ItemName, Spec, Location, BoxID, Quantity, UpdateTime
                FROM `Item List`
                WHERE SN = %s
            """
            result = db_config.execute_query(query, (sn,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"取得物品失敗: {e}")
            return None
    
    @staticmethod
    def add_item(item_data):
        try:
            sn = item_data.get('SN') or str(uuid.uuid4())
            query = """
                INSERT INTO `Item List` (SN, ItemName, Spec, Location, BoxID, Quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                sn,
                item_data.get('ItemName'),
                item_data.get('Spec', ''),
                item_data.get('Location', ''),
                item_data.get('BoxID'),
                item_data.get('Quantity', 0)
            )
            affected = db_config.execute_update(query, params)
            if affected > 0:
                logger.info(f"✅ 新增物品: {sn}")
                return sn
            return None
        except Exception as e:
            logger.error(f"新增物品失敗: {e}")
            return None
    
    @staticmethod
    def update_item(sn, item_data):
        try:
            query = """
                UPDATE `Item List`
                SET ItemName = %s, Spec = %s, Location = %s, BoxID = %s
                WHERE SN = %s
            """
            params = (
                item_data.get('ItemName'),
                item_data.get('Spec', ''),
                item_data.get('Location', ''),
                item_data.get('BoxID'),
                sn
            )
            affected = db_config.execute_update(query, params)
            return affected > 0
        except Exception as e:
            logger.error(f"更新物品失敗: {e}")
            return False
    
    @staticmethod
    def update_quantity(sn, quantity):
        try:
            query = "UPDATE `Item List` SET Quantity = %s WHERE SN = %s"
            affected = db_config.execute_update(query, (quantity, sn))
            return affected > 0
        except Exception as e:
            logger.error(f"更新庫存失敗: {e}")
            return False
    
    @staticmethod
    def delete_item(sn):
        try:
            query = "DELETE FROM `Item List` WHERE SN = %s"
            affected = db_config.execute_update(query, (sn,))
            return affected > 0
        except Exception as e:
            logger.error(f"刪除物品失敗: {e}")
            return False
    
    @staticmethod
    def search_items(keyword, box_id=None):
        try:
            if box_id:
                query = """
                    SELECT SN, ItemName, Spec, Location, BoxID, Quantity, UpdateTime
                    FROM `Item List`
                    WHERE BoxID = %s AND (ItemName LIKE %s OR Spec LIKE %s)
                    ORDER BY ItemName
                """
                params = (box_id, f'%{keyword}%', f'%{keyword}%')
            else:
                query = """
                    SELECT SN, ItemName, Spec, Location, BoxID, Quantity, UpdateTime
                    FROM `Item List`
                    WHERE ItemName LIKE %s OR Spec LIKE %s
                    ORDER BY ItemName
                """
                params = (f'%{keyword}%', f'%{keyword}%')
            return db_config.execute_query(query, params)
        except Exception as e:
            logger.error(f"搜尋物品失敗: {e}")
            return []

# ==================== 3. 交易記錄操作 ====================
class TransactionLogOperations:
    """交易記錄操作"""
    
    @staticmethod
    def add_transaction(trans_data):
        try:
            query = """
                INSERT INTO TransactionLog 
                (SN, ActionType, FromBoxID, ToBoxID, TransQty, StockBefore, StockAfter, Operator, Remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                trans_data.get('SN'),
                trans_data.get('ActionType'),
                trans_data.get('FromBoxID', '0'),
                trans_data.get('ToBoxID', '0'),
                trans_data.get('TransQty'),
                trans_data.get('StockBefore', 0),
                trans_data.get('StockAfter', 0),
                trans_data.get('Operator', 'System'),
                trans_data.get('Remark', '')
            )
            
            with db_config.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                log_id = cursor.lastrowid
                conn.commit()
                cursor.close()
            
            logger.info(f"✅ 新增交易記錄: {log_id}")
            return log_id
        except Exception as e:
            logger.error(f"新增交易記錄失敗: {e}")
            return None
    
    @staticmethod
    def stock_in(sn, quantity, to_box_id, operator, remark=''):
        try:
            item = ItemOperations.get_item_by_sn(sn)
            if not item:
                logger.error(f"物品 {sn} 不存在")
                return False
            
            stock_before = item['Quantity']
            stock_after = stock_before + quantity
            
            if not ItemOperations.update_quantity(sn, stock_after):
                return False
            
            trans_data = {
                'SN': sn, 'ActionType': '入庫',
                'FromBoxID': '0', 'ToBoxID': to_box_id,
                'TransQty': quantity,
                'StockBefore': stock_before, 'StockAfter': stock_after,
                'Operator': operator, 'Remark': remark
            }
            
            log_id = TransactionLogOperations.add_transaction(trans_data)
            return log_id is not None
        except Exception as e:
            logger.error(f"入庫操作失敗: {e}")
            return False
    
    @staticmethod
    def stock_out(sn, quantity, from_box_id, operator, remark=''):
        try:
            item = ItemOperations.get_item_by_sn(sn)
            if not item:
                return False
            
            stock_before = item['Quantity']
            if stock_before < quantity:
                logger.error(f"庫存不足")
                return False
            
            stock_after = stock_before - quantity
            if not ItemOperations.update_quantity(sn, stock_after):
                return False
            
            trans_data = {
                'SN': sn, 'ActionType': '出庫',
                'FromBoxID': from_box_id, 'ToBoxID': '0',
                'TransQty': quantity,
                'StockBefore': stock_before, 'StockAfter': stock_after,
                'Operator': operator, 'Remark': remark
            }
            
            log_id = TransactionLogOperations.add_transaction(trans_data)
            return log_id is not None
        except Exception as e:
            logger.error(f"出庫操作失敗: {e}")
            return False
    
    @staticmethod
    def transfer(sn, quantity, from_box_id, to_box_id, operator, remark=''):
        try:
            item = ItemOperations.get_item_by_sn(sn)
            if not item:
                return False
            
            stock_before = item['Quantity']
            stock_after = stock_before
            
            trans_data = {
                'SN': sn, 'ActionType': '調撥',
                'FromBoxID': from_box_id, 'ToBoxID': to_box_id,
                'TransQty': quantity,
                'StockBefore': stock_before, 'StockAfter': stock_after,
                'Operator': operator, 'Remark': remark
            }
            
            log_id = TransactionLogOperations.add_transaction(trans_data)
            if log_id:
                ItemOperations.update_item(sn, {'BoxID': to_box_id, 'ItemName': item['ItemName']})
            
            return log_id is not None
        except Exception as e:
            logger.error(f"調撥操作失敗: {e}")
            return False
    
    @staticmethod
    def get_transactions(limit=100, sn=None, action_type=None):
        try:
            query = """
                SELECT LogID, SN, ActionType, FromBoxID, ToBoxID, 
                       TransQty, StockBefore, StockAfter, Operator, Remark, Timestamp
                FROM TransactionLog
            """
            params = []
            conditions = []
            
            if sn:
                conditions.append("SN = %s")
                params.append(sn)
            if action_type:
                conditions.append("ActionType = %s")
                params.append(action_type)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY Timestamp DESC LIMIT %s"
            params.append(limit)
            
            return db_config.execute_query(query, tuple(params))
        except Exception as e:
            logger.error(f"取得交易記錄失敗: {e}")
            return []
    
    @staticmethod
    def get_transaction_by_id(log_id):
        try:
            query = """
                SELECT LogID, SN, ActionType, FromBoxID, ToBoxID,
                       TransQty, StockBefore, StockAfter, Operator, Remark, Timestamp
                FROM TransactionLog
                WHERE LogID = %s
            """
            result = db_config.execute_query(query, (log_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"取得交易記錄失敗: {e}")
            return None