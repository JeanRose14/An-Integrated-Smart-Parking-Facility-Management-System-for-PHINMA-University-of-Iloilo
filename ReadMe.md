# An Integrated Smart Parking Facility Management System for PHINMA University of Iloilo

A web-based parking management system that uses **RFID technology** to automatically track vehicle entry and exit at the university parking facility, providing **real-time monitoring** through a live dashboard powered by WebSockets.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Routes & Endpoints](#routes--endpoints)
- [How It Works](#how-it-works)

---

## Features

- **User Authentication** — Secure registration and login with hashed passwords (werkzeug)
- **RFID-Based Tracking** — Automatic time-in/time-out logging when RFID tags are scanned
- **Real-Time Dashboard** — Live parking statistics (available/occupied/total slots) updated via Socket.IO
- **Parking Logs** — Complete history of all parking activity with status tracking
- **Vehicle Monitoring** — View all vehicles currently inside the parking facility
- **User Management** — View registered users and their assigned RFID tags
- **REST API** — JSON endpoint for parking status data (`/api/parking-status`)
- **Parking Full Alert** — Visual alert when all parking slots are occupied

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Flask (Python)                      |
| Database   | MySQL                               |
| Real-Time  | Flask-SocketIO (WebSockets)         |
| Frontend   | HTML5, CSS3, JavaScript, Jinja2     |
| Security   | werkzeug (password hashing)         |
| Hardware   | RFID Readers (serial communication) |

---

## System Architecture

```
RFID Reader
    │
    ▼
Serial Listener (serial_listener.py)
    │
    ▼ POST /update-parking
Flask Application (app.py)
    ├──► MySQL Database (pk_db)
    │       ├── registered (users)
    │       ├── parking_logs (activity)
    │       └── rfid_logs (raw scans)
    │
    └──► Socket.IO Broadcast
            │
            ▼
        Dashboard (real-time updates)
```

---

## Prerequisites

- **Python** 3.8 or higher
- **MySQL** 5.7 or higher
- **pip** (Python package manager)
- **RFID Reader** hardware (for production use)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/An-Integrated-Smart-Parking-Facility-Management-System-for-PHINMA-University-of-Iloilo.git
   cd An-Integrated-Smart-Parking-Facility-Management-System-for-PHINMA-University-of-Iloilo
   ```

2. **Create a virtual environment** (recommended)

   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux/macOS
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install flask flask-mysqldb flask-socketio werkzeug
   ```

---

## Database Setup

1. **Create the database and tables** in MySQL:

   ```sql
   CREATE DATABASE pk_db;
   USE pk_db;

   CREATE TABLE registered (
       id INT AUTO_INCREMENT PRIMARY KEY,
       full_name VARCHAR(255) NOT NULL,
       email VARCHAR(255) UNIQUE NOT NULL,
       vehicle_plate_number VARCHAR(50),
       password VARCHAR(255) NOT NULL,
       rfid VARCHAR(100) DEFAULT NULL
   );

   CREATE TABLE parking_logs (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id INT DEFAULT NULL,
       rfid VARCHAR(100) NOT NULL,
       time_in DATETIME,
       time_out DATETIME DEFAULT NULL,
       status VARCHAR(20) DEFAULT 'Inside',
       FOREIGN KEY (user_id) REFERENCES registered(id)
   );

   CREATE TABLE rfid_logs (
       id INT AUTO_INCREMENT PRIMARY KEY,
       uid VARCHAR(100) NOT NULL
   );
   ```

2. **Configure database credentials** in `app.py`:

   ```python
   app.config['MYSQL_HOST'] = 'localhost'
   app.config['MYSQL_USER'] = 'root'
   app.config['MYSQL_PASSWORD'] = 'your_password'
   app.config['MYSQL_DB'] = 'pk_db'
   app.config['MYSQL_PORT'] = 3306
   ```

---

## Running the Application

```bash
python app.py
```

The application will start at **http://localhost:5000**.

---

## Project Structure

```
├── app.py                     # Main Flask application (routes, socket events)
├── controllers/
│   └── controllers.py         # Route handlers
├── models/
│   └── models.py              # Database query functions
├── templates/
│   ├── intro.html             # Landing page
│   ├── login.html             # User login
│   ├── register.html          # User registration
│   ├── dashboard.html         # Real-time parking dashboard
│   ├── parking_logs.html      # Parking activity logs
│   ├── users.html             # Registered users list
│   └── vehicles_inside.html   # Currently parked vehicles
├── static/
│   ├── style.css              # Global styles
│   ├── bg.jpg                 # Background image
│   ├── univ.png               # University logo
│   └── cite.png               # Citation image
└── ReadMe.md
```

---

## Routes & Endpoints

| Route                  | Method     | Description                          |
|------------------------|------------|--------------------------------------|
| `/`                    | GET        | Landing page                         |
| `/login`               | GET, POST  | User login                           |
| `/register`            | GET, POST  | User registration                    |
| `/dashboard`           | GET        | Real-time parking dashboard          |
| `/update-parking`      | POST       | Process RFID scan (time in/out)      |
| `/parking_logs`        | GET        | View all parking activity logs       |
| `/users`               | GET        | List registered users                |
| `/vehicles_inside`     | GET        | View vehicles currently parked       |
| `/logout`              | GET        | Clear session and redirect to login  |
| `/api/parking-status`  | GET        | JSON API for parking availability    |

### API Response Example

**GET** `/api/parking-status`

```json
{
  "available": 3,
  "occupied": 2,
  "total": 5
}
```

---

## How It Works

1. **Vehicle arrives** — The RFID reader scans the vehicle's RFID tag
2. **Serial listener** sends the RFID data to `/update-parking` via POST request
3. **System checks** if the RFID has an active "Inside" status in `parking_logs`
   - **If not inside** — Creates a new log entry with `time_in = NOW()` and `status = 'Inside'`
   - **If already inside** — Updates the existing log with `time_out = NOW()` and `status = 'Completed'`
4. **Parking state updates** — Available/total slot counts are refreshed in memory
5. **Dashboard refreshes** — All connected clients receive real-time updates via Socket.IO

---

## Contributors

- PHINMA University of Iloilo — College of Information Technology Education