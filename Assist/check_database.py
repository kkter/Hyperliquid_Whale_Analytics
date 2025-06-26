import sqlite3

# 连接到 .db 文件
db_path = '/Users/kkter/KKTer/Learn_File/Programing/Project/Hyperliquid_Whale/whale_tracker.db'  # 替换为你的 .db 文件路径
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("数据库中的表：", [table[0] for table in tables])

# 遍历每个表并查看其内容
for table in tables:
    table_name = table[0]
    print(f"\n表 '{table_name}' 的内容：")
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    print("表结构（列名）：", [col[1] for col in columns])
    
    # 获取表数据
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

# 关闭连接
conn.close()