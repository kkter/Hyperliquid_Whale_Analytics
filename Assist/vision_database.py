import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 假设数据已加载到 DataFrame
# 如果需要从数据库读取：
db_path = 'whale_tracker.db'  # 替换为你的 .db 文件路径
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM position_details", conn)
conn.close()

# 按资产类型汇总持仓规模
asset_size = df.groupby('asset')['position_size_usd'].sum().sort_values(ascending=False)

# 绘制柱状图
plt.figure(figsize=(12, 6))
sns.barplot(x=asset_size.index, y=asset_size.values, palette='viridis')
plt.xlabel('资产类型')
plt.ylabel('总持仓规模 (USD)')
plt.title('各资产类型的总持仓规模')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()