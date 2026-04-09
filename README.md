# 🏡 Home Services App

A robust Django-based ecosystem for managing, monitoring, and automating Home Server services. The project is containerized and designed to run on Linux servers, featuring a mirrored development environment and advanced maintenance tools.

## ✨ Key Features

* **📡 Internet Monitoring (`internet_status`):**
  * Continuous status checking (Ping).
  * Automated speed tests via the official Ookla CLI.
  * **WAF Evasion (Jitter):** An intelligent system of randomized execution windows calculated via CRON to prevent IP blocking caused by request patterning.
* **⏰ Custom Hybrid Scheduler:**
  * Proprietary task scheduler built as a Django management command (`scheduler.py`).
  * *Multithreading* execution, eliminating the need for heavy messaging brokers like Celery or Redis.
  * Supports static scheduling via JSON and dynamic loading directly from the Database using CRON expressions (`croniter`).
* **🔔 Alert System:**
  * Direct integration with the MailerSend REST API for transactional email notifications in the event of network outages or severe slowdowns.
* **🛡️ Bulletproof Dependency Management:**
  * Smart update script (`update-reqs.sh`) featuring deep auditing via pip's Dependency Resolver, auto-heal attempts, and automatic rollback to prevent Python environment corruption.
* **🔄 Secure Prod ➡️ Dev Sync:**
  * Seamless data flow via *SSH Streaming* (zero temporary files left on the production server).
  * Automated shell scripts to securely fetch and load the production database directly into the local environment or the development Docker container.

## 🛠️ Tech Stack

* **Backend:** Python 3.13+ / Django
* **Database:** PostgreSQL 18
* **Infrastructure:** Docker, Docker Compose, Nginx
* **Core Libraries:** `schedule`, `croniter`, `requests` (MailerSend API integration)
* **Dev Environment:** Linux (Debian / Ubuntu / WSL)

---

## 🚀 Getting Started (Development Environment)

### 1. Clone the repository
```bash
git clone [https://github.com/danielcdias/home-services.git](https://github.com/danielcdias/home-services.git)
cd home-services
```

### 2. Configure Environment Variables
Create a `.env` file in the project root based on `.env.example`  and fill in your local credentials.

### 3. Spin up the Infrastructure (Docker)
The development environment uses the `compose.dev.yaml` file, which exposes internal ports and maps volumes for *hot-reloading*.
```bash
docker compose -f compose.dev.yaml up -d --build
```
The application will be available at `http://localhost`.

---

## 🧰 Developer Toolbox (Maintenance Scripts)

The project includes several Bash scripts in the root directory to automate the development lifecycle:

### 📦 Data Synchronization (Prod to Dev)
To mirror the Home Server production data into your local development machine:

1. **Fetch the Dump:** Connects via SSH and streams the database in real-time.
   ```bash
   ./fetch-prod-data.sh
   # Optional: ./fetch-prod-data.sh YYYY-MM-DD to filter logs from a specific date
   ```
2. **Load into Dev Docker:** Injects the downloaded data into the development container. The script intelligently spins up the environment if it's down and flushes the current DB before loading.
   ```bash
   ./load-docker-dev.sh
   ```
*(Note: Use `./load-local-dev.sh` if you are running Django natively on Linux without Docker).*

### 🐍 Python Package Updates
To safely upgrade all dependencies in your `requirements.txt`:
```bash
# Upgrades packages, resolves dependencies, and audits for conflicts
./update-reqs.sh --upgrade-all  # or ./update-reqs.sh -u

# Only regenerates the requirements.txt file with the current state
./update-reqs.sh
```

---

## 🏗️ Docker Compose Structure

* **`compose.yaml` (Production):** Focused on security, uses isolated networks (`internal_db`), strict restart policies, and communicates exclusively via Reverse Proxy.
* **`compose.dev.yaml` (Development):** Focused on agility, exposes PostgreSQL ports for local GUI inspection, and uses bind mounts for real-time source code synchronization.
