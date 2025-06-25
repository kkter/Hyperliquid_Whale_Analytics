# Hyperliquid Whale Analytics

## 项目简介

本项目是一个自动化的 Hyperliquid 巨鲸持仓追踪与分析平台。系统定时爬取 Coinglass Hyperliquid 排行榜，结合官方 API 获取鲸鱼的实时持仓数据，并通过 Flask Web 应用进行可视化展示。  
主要功能包括：

- 实时巨鲸排行榜与仓位详情
- 多空情绪与资产分布可视化
- 鲸鱼历史持仓与行为分析
- 自动化数据采集与仓位更新
- 支持 Docker Compose 多进程部署，数据与日志持久化

---

## 目录结构

```
/home/kkter/app/Hyperliquid_Whale_Analytics/
├── app.py
├── get_address.py
├── update_positions.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── templates/
├── data/         # 持久化数据库目录
└── logs/         # 持久化日志目录（可选）
```

---

## 快速部署

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
```

### 2. 创建持久化目录

```bash
mkdir -p data logs
```

### 3. 配置 Docker Compose 网络

确保 `docker-compose.yml` 中包含：

```yaml
networks:
  app_network:
    external: true
```
并且 `app_network` 已经存在。

### 4. 构建并启动服务

```bash
docker-compose up -d
```

### 5. 访问服务

浏览器访问：http://<服务器IP>:5000

---

## 说明

- 数据库和日志文件分别持久化在 `data/` 和 `logs/` 目录下，便于备份和迁移。
- 三个服务（Web、排行榜爬虫、仓位更新）均为独立进程，互不影响。
- 所有服务通过 `app_network` 网络互联。

---