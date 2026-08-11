# Hyperliquid 大户持仓分析

一个自托管的数据管道与仪表盘，用于研究第三方 Hyperliquid 排行榜中账户的公开持仓。

## 主要功能

- 每四小时使用 Selenium 采集最多 20 条排行榜记录
- 将地址、资产、排名和采集时间保存为历史快照
- 每五分钟轮询 Hyperliquid 公共 `clearinghouseState` 接口
- 在 SQLite 中规范化保存仓位价值、方向、未实现盈亏、杠杆和入场价格
- 通过 Flask 仪表盘展示当前仓位、市场汇总与排名历史

本应用仅进行只读分析，不需要钱包私钥，也不会提交交易。

## 架构

```text
第三方排行榜
      │ Selenium / Beautiful Soup（每 4 小时）
      ▼
 leaderboard_snapshots ───────┐
 addresses                    │
                              ├──► SQLite ──► Flask + Chart.js
 Hyperliquid 公共 API         │
      │ HTTP 轮询（每 5 分钟）
      ▼                       │
 position_details ────────────┘
```

Docker Compose 从同一镜像运行三个服务：

| 服务 | 职责 |
| --- | --- |
| `get_address` | 维护地址列表与排行榜历史快照 |
| `update_positions` | 通过 Hyperliquid API 刷新未平仓仓位 |
| `web` | 使用 Gunicorn 提供仪表盘和 JSON API |

## 快速开始

### 要求

- Docker 与 Compose 插件
- 能访问排行榜和 Hyperliquid API 的网络
- 名为 `app_network` 的 Docker 网络

```bash
git clone https://github.com/kkter/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
docker network create app_network
mkdir -p data logs
docker compose up -d --build
```

访问 `http://localhost:5000`。如果 `app_network` 已存在，可跳过创建网络的命令。

仓库包含一份示例 SQLite 快照，便于立即查看界面；后续数据会持久化到 `data/`。

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data logs
python get_address.py
```

地址采集器初始化数据库后，在另外两个终端分别运行 `update_positions.py` 与 `app.py`。Flask 开发服务器使用 `5000` 端口。

## Web 路由

| 路由 | 用途 |
| --- | --- |
| `GET /` | 当前排行榜与仓位仪表盘 |
| `GET /whale/<address>` | 单个地址的当前仓位 |
| `GET /api/market_overview` | 聚合仓位与多空数据 |
| `GET /api/whale_history/<address>` | 单个地址的历史排名序列 |

## 运行说明

- 排行榜采集依赖第三方页面结构；上游改版后可能需要更新选择器。
- `webdriver-manager` 会在运行时下载浏览器驱动；生产环境建议固定或预装浏览器与驱动版本。
- 仪表盘显示最近一次成功轮询的公共数据，不是面向交易执行的实时行情源。
- 本项目不提供交易信号或投资建议。
