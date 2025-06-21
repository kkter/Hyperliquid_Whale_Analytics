import sqlite3
import pandas as pd

# 连接到 .db 文件
db_path = 'whale_tracker.db'  # 替换为你的 .db 文件路径
conn = sqlite3.connect(db_path)

# 查看所有表名
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("数据库中的表：", [table[0] for table in tables])

# 读取某个表的数据到 DataFrame
table_name = 'position_details'  # 替换为你要可视化的表名
df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

# 关闭连接
conn.close()

# 查看 DataFrame
print(df.head())