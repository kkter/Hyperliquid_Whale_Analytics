
whale_tracker.db 是一个 SQLite 数据库文件，它就像一个专门为您这个项目设计的、轻量级的“数据仓库”。根据我们之前的规划和代码，这个数据库文件里主要包含 三张表，它们协同工作，存储着您项目的所有核心数据。

以下是每张表的内容和作用：

1. addresses 表
这张表是您所有数据的核心注册表，它只存储独一无二的鲸鱼地址。

作用: 确保每个被追踪的鲸鱼地址只被记录一次，并作为其他数据表的关联中心。
内容:
address: 鲸鱼的钱包地址 (例如: 0x5b5d...c060)。这是主键，不会重复。
first_seen: 这个地址第一次被您的爬虫发现的时间。
notes: 您为这个地址添加的备注（目前为空）。


2. leaderboard_snapshots 表
这张表是您从 Coinglass 网站爬取数据的历史快照记录。

作用: 记录每一次爬虫运行时，排行榜上的情况。这让您可以分析排行榜随时间的变化。
内容:
id: 一条记录的唯一编号。
scrape_time: 这条记录被爬取的时间。
rank: 这条持仓记录在当时的排名。
asset: 对应的币种 (例如: BTC, ETH)。
whale_address: 对应的鲸鱼地址。这个地址关联到 addresses 表。


3. position_details 表
这张表存储的是您通过 Hyperliquid 官方API 获取的、最详细、最接近实时的仓位状态。

作用: 提供每个地址在每个币种上的具体持仓细节，用于前端展示和深度分析。这张表的数据会被 update_positions.py 脚本频繁更新。
内容:
id: 唯一编号。
whale_address: 鲸鱼地址。
asset: 币种。
position_size_usd: 以美元计价的仓位大小。
unrealized_pnl: 未实现的盈亏。
leverage: 使用的杠杆倍数。
entry_price: 开仓均价。
last_updated: 这条仓位信息最后一次从API更新的时间。
总结一下它们的关系：

get_address.py 负责填充 addresses 表和 leaderboard_snapshots 表。
update_positions.py 会先从 addresses 表读取所有需要追踪的地址，然后调用API，最后将获取到的详细数据写入或更新到 position_details 表中。
这种结构将“低频的历史快照”和“高频的实时状态”清晰地分离开来，是一个非常健壮和可扩展的设计。


4. sqlite_sequence

sqlite_sequence 是一个由 SQLite 数据库自己自动创建和管理的内部表。您不需要也不应该手动去修改它。

它的作用很简单：记录使用了 AUTOINCREMENT 关键字的表中，自增ID已经用到的最大值。

是什么？ SQLite的内部管理表。
为什么有？ 因为您的 leaderboard_snapshots 和 position_details 表使用了 AUTOINCREMENT。
需要管它吗？ 完全不需要。您可以放心地忽略它，把它看作是SQLite正常工作的一部分即可。