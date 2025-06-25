# Hyperliquid Whale Analytics

## Project Introduction

This project is an automated Hyperliquid whale position tracking and analytics platform.  
It periodically scrapes the Coinglass Hyperliquid leaderboard, fetches real-time whale position data via the official API, and visualizes everything through a Flask web application.

**Key features:**

- Real-time whale leaderboard and position details
- Visualization of long/short sentiment and asset distribution
- Whale historical position and behavior analysis
- Automated data collection and position updates
- Supports multi-process Docker Compose deployment with persistent data and logs

---

## Directory Structure

```
/home/kkter/app/Hyperliquid_Whale_Analytics/
├── app.py
├── get_address.py
├── update_positions.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── templates/
├── data/         # Persistent database directory
└── logs/         # Persistent log directory (optional)
```

---

## Quick Deployment

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/Hyperliquid_Whale_Analytics.git
cd Hyperliquid_Whale_Analytics
```

### 2. Create persistent directories

```bash
mkdir -p data logs
```

### 3. Docker Compose network configuration

Make sure your `docker-compose.yml` includes:

```yaml
networks:
  app_network:
    external: true
```
and that `app_network` already exists.

### 4. Build and start services

```bash
docker-compose up -d
```

### 5. Access the service

Visit in your browser: http://<server-ip>:5000

---

## Notes

- Database and log files are persisted in `data/` and `logs/` directories for easy backup and migration.
- The three services (web, leaderboard crawler, position updater) run as independent processes.
- All services are connected via the `app_network` Docker network.

---