# Hyperliquid 大户持仓分析

一个自托管的数据管道与仪表盘，用于研究已跟踪 Hyperliquid 地址的公开持仓。

## 主要功能

- 第三方排行榜不可用时仍使用仓库内已有地址持续工作
- 每五分钟通过超时与重试机制轮询 Hyperliquid 官方 `clearinghouseState` 接口
- 在 SQLite 中规范化保存仓位价值、方向、未实现盈亏、杠杆和入场价格
- API 请求失败时保留该地址最近一次成功仓位
- 仅在官方响应有效时清理已平仓仓位，并原子发布单地址更新
- 可选使用 Selenium 采集第三方排名，作为历史补充信息
- 使用 SQLite WAL、忙等待、同步状态和生产健康检查

本应用仅进行只读分析，不需要钱包私钥，也不会提交交易。

## 架构

```text
地址列表 ──► Hyperliquid 官方 API ──► 最近成功仓位
   ▲                                  │
   │                                  ▼
可选 Coinglass 采集器 ──► 排名历史   SQLite ──► Flask
```

Docker Compose 默认运行两个服务，并提供一个可选 profile：

| 服务 | 职责 |
| --- | --- |
| `coinglass_collector` | 可选 `coinglass` profile，用于补充排名与地址 |
| `update_positions` | 通过 Hyperliquid API 刷新未平仓仓位 |
| `web` | 使用 Gunicorn 提供仪表盘和 JSON API |

## 快速开始

### 要求

- Docker 与 Compose 插件
- 能访问 Hyperliquid API 的网络

```bash
git clone https://github.com/kkter/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
docker compose up -d --build
```

访问 `http://localhost:5103`。

仓库包含已刷新的 SQLite 快照与已跟踪地址，便于立即查看界面；后续数据会持久化到 `data/`。

默认部署不依赖 Coinglass。如需启用可失败降级的浏览器采集器：

```bash
docker compose --profile coinglass up -d
```

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
RUN_ONCE=1 python update_positions.py
python app.py
```

若需持续刷新，可在另一终端直接运行 `update_positions.py`（不设置 `RUN_ONCE`）。`get_address.py` 是可选补充源。

## 配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DATABASE_FILE` | `data/whale_tracker.db` | 持久化 SQLite 数据库 |
| `POSITION_POLL_SECONDS` | `300` | 官方 API 刷新间隔 |
| `WHALES_BIND_ADDRESS` | `127.0.0.1` | Docker 宿主机绑定地址 |
| `WHALES_PORT` | `5103` | Docker 宿主机端口 |
| `COINGLASS_LOOP` | `0` | 是否重复运行可选采集器 |

## Web 路由

| 路由 | 用途 |
| --- | --- |
| `GET /` | 当前排行榜与仓位仪表盘 |
| `GET /whale/<address>` | 单个地址的当前仓位 |
| `GET /api/market_overview` | 聚合仓位与多空数据 |
| `GET /api/whale_history/<address>` | 单个地址的历史排名序列 |
| `GET /healthz` | 数据库就绪状态与完整性检查 |

## 运行说明

- 可选排行榜采集依赖第三方页面结构，可能需要更新选择器；失败不会影响仪表盘或官方 API 更新器。
- Chromium 与 ChromeDriver 一起从 Debian 镜像仓库安装，运行时不再下载驱动。
- 仪表盘显示最近一次成功轮询的公共数据，不是面向交易执行的实时行情源。
- 本项目不提供交易信号或投资建议。
