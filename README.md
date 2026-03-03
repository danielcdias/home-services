# 🏠 Home Services

**Home Services** is a Django-based ecosystem created to centralize the management, automation, and monitoring of a smart home. Designed to run on a local Home Server, the project is built with a modular architecture: each home feature acts as an independent "app", but they all share the same administrative panel and database.

---

## 🧩 Current Modules

### 1. 🌐 Internet Status (`internet_status`)
The first active module in the ecosystem. A robust system for continuous monitoring of residential internet quality.
* **Multi-Provider Monitoring:** Compares the delivered speed against the contracted speed across multiple ISPs simultaneously.
* **Speedtest & Latency:** In-depth history of Download, Upload, IP, ISP details, and automatic calculation of the geographic distance to the test server.
* **Stability & Alerts:** Recurring ping tests to calculate success rates and track downtime.
* **Custom Hybrid Scheduler:** A built-in multithreaded task engine. It reads routine tasks from a `scheduled-tasks.json` file and dynamically from the PostgreSQL database. Features *Hot-Reload*, updating test schedules in real-time as they are edited in the admin panel, without needing restarts or heavy queues like Redis/Celery.
* **Visual Dashboards:** Interactive charts (Chart.js), annual/monthly summaries, and responsive reports formatted for A4 printing.

---

## 🚀 Roadmap and Future Module Ideas

The flexible architecture allows new apps to be plugged into the server as the home evolves. Some planned or suggested expansions:

* **🛠️ Maker Space (`maker_hub`):** A manager for DIY projects. Tracks electronic component inventory (LEDs, buttons, Arduinos), manages 3D printing queues (to keep track of sliced vs. printed models), and monitors project expenses.
* **🧸 Family Hub (`family_hub`):** An interactive dashboard focused on children's routines. It could include an achievement board or daily tasks (like brushing teeth, tidying up toys) with visual rewards, and a central family calendar.
* **🖥️ Network & Ad-Block Dashboard (`net_dashboard`):** A central interface to consolidate data from other network services (like Pi-hole ad-blocking stats or OpenWRT router status), all within the same Django dashboard.
* **🔐 Home Vault (`home_vault`):** Management of local software licenses, guest Wi-Fi keys (generating dynamic QR Codes), and a home equipment inventory (tracking warranty dates).

---

## 🛠️ Global Tech Stack

* **Backend:** Python 3, Django
* **Database:** PostgreSQL
* **Background Tasks:** Native Multithreaded Hybrid Scheduler (`schedule` library)
* **Frontend:** HTML5, Bootstrap 5, Vanilla JS, Pure CSS (with dynamic tooltips injected via JS)
* **Infrastructure:** Docker & Docker Compose (Optimized for Linux/MiniPC architectures)

---

## ⚙️ How to Run the Project (Via Docker)

The environment is fully containerized for easy deployment on your local server.

### 1. Basic Installation
Clone the repository to your server:
```bash
git clone [https://github.com/danielcdias/home-services.git](https://github.com/danielcdias/home-services.git)
cd home-services
```

### 2. Spinning up the Infrastructure
Build the images and start the database, web server, and background scheduler services:
```bash
docker compose up -d --build
```

### 3. Initial Configuration
Create an administrator user to access the Django control panel:
```bash
docker compose exec web python manage.py createsuperuser
```

### 4. Access
* **Application Dashboard (Frontend):** `http://localhost:8000`
* **Management Panel (Admin):** `http://localhost:8000/admin`

---

## 📝 License

This project was developed for personal use, continuous learning, and home automation. Feel free to fork it and adapt the ecosystem for your own home!

Developed with ☕ and 🐍 by [Daniel Dias](https://github.com/danielcdias).
