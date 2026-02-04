# db_config.py
"""
MariaDB 資料庫連接配置
HOST: 192.168.0.10
DATABASE: deinventory
USER: linebot
"""
import pymysql
from pymysql import Error
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 資料庫連接配置 ====================
DB_CONFIG = {
    'host': '192.168.0.10',
    'port': 3306,
    'database': 'deinventory',
    'user': 'linebot',
    'password': 'Linebot@85079870',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
    'connect_timeout': 10
}

@contextmanager
def get_db_connection():
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        yield connection
    except Error as e:
        if connection:
            connection.rollback()
        logger.error(f"資料庫操作錯誤: {e}")
        raise
    finally:
        if connection:
            connection.close()

def get_connection():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logger.error(f"資料庫連接錯誤: {e}")
        raise

def test_connection():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        logger.info(f"✅ 資料庫連接成功: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
        return True
    except Error as e:
        logger.error(f"❌ 資料庫連接失敗: {e}")
        return False

def execute_query(query, params=None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
        return result
    except Error as e:
        logger.error(f"查詢執行錯誤: {e}")
        logger.error(f"SQL: {query}")
        raise

def execute_update(query, params=None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            affected_rows = cursor.execute(query, params or ())
            conn.commit()
            cursor.close()
        return affected_rows
    except Error as e:
        logger.error(f"更新執行錯誤: {e}")
        raise

INIT_SQL = """
CREATE TABLE IF NOT EXISTS MaterialOverview (
    BoxID VARCHAR(50) PRIMARY KEY,
    Category VARCHAR(100),
    Description TEXT,
    Owner VARCHAR(100),
    Status VARCHAR(50) DEFAULT '使用中',
    CreateDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (Category),
    INDEX idx_status (Status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MaterialItems (
    SN VARCHAR(100) PRIMARY KEY,
    ItemName VARCHAR(200) NOT NULL,
    Spec VARCHAR(200),
    Location VARCHAR(200),
    BoxID VARCHAR(50),
    Quantity INT DEFAULT 0,
    UpdateTime DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_boxid (BoxID),
    FOREIGN KEY (BoxID) REFERENCES MaterialOverview(BoxID) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MaterialTransaction (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    SN VARCHAR(100),
    ActionType VARCHAR(50),
    FromBoxID VARCHAR(50),
    ToBoxID VARCHAR(50),
    TransQty INT,
    StockBefore INT,
    StockAfter INT,
    Operator VARCHAR(100),
    Remark TEXT,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sn (SN),
    FOREIGN KEY (SN) REFERENCES MaterialItems(SN) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

def initialize_database():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for stmt in INIT_SQL.split(';'):
                if stmt.strip():
                    cursor.execute(stmt)
            conn.commit()
            cursor.close()
        logger.info("✅ 資料庫初始化完成")
        return True
    except Error as e:
        logger.error(f"❌ 初始化失敗: {e}")
        return False

if __name__ == "__main__":
    print("測試資料庫連接...")
    print(f"HOST: {DB_CONFIG['host']}")
    print(f"DATABASE: {DB_CONFIG['database']}")
    print(f"USER: {DB_CONFIG['user']}")
    if test_connection():
        print("✅ 連接成功!")
    else:
        print("❌ 連接失敗!")
