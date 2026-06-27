from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "smartpark-secret-key-2026"

# ================= MYSQL CONFIG =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rose@1406'
app.config['MYSQL_DB'] = 'pk_db'
app.config['MYSQL_PORT'] = 3306

mysql = MySQL(app)

# ================= PARKING STATE =================
latest_parking = {"available": 5, "total": 5}

# ================= LANDING =================
@app.route('/')
def landing_page():
    return render_template('intro.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, full_name, password, role FROM registered WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_email'] = email
            session['user_name'] = user[1]
            session['user_role'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')

# ================= REGISTER (ADMIN/STAFF) =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email', '').lower().strip()
        password = generate_password_hash(request.form.get('password'))
        role = request.form.get('role', 'Staff')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM registered WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered!", "warning")
            cur.close()
            return render_template('register.html')

        cur.execute("""
            INSERT INTO registered (full_name, email, password, role, date_registered, expiration_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, email, password, role, datetime.now(), datetime.now() + timedelta(days=365)))
        mysql.connection.commit()
        cur.close()

        flash("Account created! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# ================= REGISTER USER (ADMIN ADDS PARKING USERS) =================
@app.route('/reg-user', methods=['GET', 'POST'])
def reg_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email', '').lower().strip()
        plate = request.form.get('vehicle_plate_number')
        rfid = request.form.get('rfid')
        role = request.form.get('role', 'Student')
        password = generate_password_hash(request.form.get('password', 'parking123'))

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM registered WHERE email=%s OR rfid=%s", (email, rfid))
            if cur.fetchone():
                flash("User with that email or RFID already exists!", "warning")
                cur.close()
                return render_template('reg_user.html')

            cur.execute("""
                INSERT INTO registered
                (full_name, email, vehicle_plate_number, rfid, role, password, date_registered, expiration_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (full_name, email, plate, rfid, role, password, datetime.now(), datetime.now() + timedelta(days=365)))
            mysql.connection.commit()
            cur.close()

            flash("User registered successfully!", "success")

        except Exception as e:
            print("ERROR:", e)
            flash("Registration failed. Please try again.", "danger")

    return render_template('reg_user.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM parking_logs WHERE status='Inside'")
    occupied = cur.fetchone()[0]

    total = latest_parking["total"]
    available = total - occupied

    cur.execute("SELECT time_in FROM parking_logs ORDER BY time_in DESC LIMIT 1")
    last_in = cur.fetchone()
    last_scan_in = last_in[0].strftime("%I:%M:%S %p") if last_in and last_in[0] else "--"

    cur.execute("SELECT time_out FROM parking_logs WHERE time_out IS NOT NULL ORDER BY time_out DESC LIMIT 1")
    last_out = cur.fetchone()
    last_scan_out = last_out[0].strftime("%I:%M:%S %p") if last_out and last_out[0] else "--"

    cur.execute("SELECT COUNT(*) FROM registered")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM parking_logs WHERE status='Inside'")
    vehicles_inside = cur.fetchone()[0]

    cur.close()
    latest_parking["available"] = available

    return render_template('dashboard.html',
        available=available, occupied=occupied, total=total,
        last_scan_in=last_scan_in, last_scan_out=last_scan_out,
        total_users=total_users, vehicles_inside=vehicles_inside)

# ================= RFID MAIN LOGIC =================
@app.route('/update-parking', methods=['POST'])
def update_parking():
    data = request.get_json()
    rfid = data.get("rfid")
    available = data.get("available")
    total = data.get("total")

    if not rfid:
        return jsonify({"error": "No RFID"}), 400

    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT id, user_id FROM parking_logs WHERE rfid=%s AND status='Inside' LIMIT 1", (rfid,))
        existing = cur.fetchone()

        if existing is None:
            cur.execute("INSERT INTO parking_logs (rfid, time_in, status) VALUES (%s, NOW(), 'Inside')", (rfid,))
            scan_type = "IN"
            cur.execute("SELECT time_in FROM parking_logs ORDER BY id DESC LIMIT 1")
        else:
            cur.execute("UPDATE parking_logs SET time_out=NOW(), status='Completed' WHERE id=%s", (existing[0],))
            scan_type = "OUT"
            cur.execute("SELECT time_out FROM parking_logs ORDER BY id DESC LIMIT 1")

        result = cur.fetchone()
        mysql.connection.commit()
        cur.close()

        now_time = result[0].strftime("%I:%M:%S %p") if result else "--"

        if available is not None and total is not None:
            latest_parking["available"] = available
            latest_parking["total"] = total

        occupied = latest_parking["total"] - latest_parking["available"]

        socketio.emit("parking_update", {
            "available": latest_parking["available"],
            "occupied": occupied,
            "total": latest_parking["total"],
            "scan_time": now_time,
            "type": scan_type
        })
        socketio.emit("new_log", {
            "rfid": rfid,
            "time": now_time,
            "type": scan_type
        })

        print("SAVED TO DB:", rfid, scan_type)

    except Exception as e:
        print("DB ERROR:", e)

    return jsonify({"status": "ok"})

# ================= PARKING LOGS =================
@app.route("/parking_logs")
def parking_logs():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.rfid, p.time_in, p.time_out, p.status, r.full_name, r.vehicle_plate_number
        FROM parking_logs p
        LEFT JOIN registered r ON p.rfid = r.rfid
        ORDER BY p.id DESC
    """)
    rows = cur.fetchall()
    cur.close()

    logs = [
        {
            "rfid": row[0],
            "time_in": row[1].strftime("%b %d, %Y %I:%M %p") if row[1] else "--",
            "time_out": row[2].strftime("%b %d, %Y %I:%M %p") if row[2] else "--",
            "status": row[3],
            "name": row[4] or "Unknown",
            "plate": row[5] or "--"
        }
        for row in rows
    ]

    return render_template("parking_logs.html", logs=logs)

# ================= USERS PAGE =================
@app.route("/users")
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("users.html")

# ================= API GET USERS =================
@app.route("/api/users")
def get_users():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, full_name, email, rfid, vehicle_plate_number, role, date_registered, expiration_date
        FROM registered ORDER BY id DESC
    """)
    rows = cur.fetchall()
    cur.close()

    users = [
        {
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "rfid": r[3] or "--",
            "plate": r[4] or "--",
            "role": r[5],
            "registered": r[6].strftime("%b %d, %Y") if r[6] else "--",
            "expires": r[7].strftime("%b %d, %Y") if r[7] else "--"
        }
        for r in rows
    ]

    return jsonify(users)

# ================= DELETE USER =================
@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM registered WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()
    socketio.emit("users_update")
    return jsonify({"status": "ok"})

# ================= EDIT USER =================
@app.route("/edit-user/<int:user_id>", methods=["POST"])
def edit_user(user_id):
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE registered
        SET full_name=%s, email=%s, rfid=%s, vehicle_plate_number=%s, role=%s
        WHERE id=%s
    """, (data.get("name"), data.get("email"), data.get("rfid"),
          data.get("plate"), data.get("role", "Student"), user_id))
    mysql.connection.commit()
    cur.close()
    socketio.emit("users_update")
    return jsonify({"status": "ok"})

# ================= VEHICLES INSIDE =================
@app.route("/vehicles_inside")
def vehicles_inside():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.rfid, p.time_in, r.full_name, r.vehicle_plate_number
        FROM parking_logs p
        LEFT JOIN registered r ON p.rfid = r.rfid
        WHERE p.status='Inside'
        ORDER BY p.time_in DESC
    """)
    rows = cur.fetchall()
    cur.close()

    vehicles = [
        {
            "rfid": v[0],
            "time_in": v[1].strftime("%b %d, %Y %I:%M %p") if v[1] else "--",
            "owner": v[2] or "Unknown",
            "plate": v[3] or "--"
        }
        for v in rows
    ]

    return render_template("vehicles_inside.html", vehicles=vehicles)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# ================= API =================
@app.route('/api/parking-status')
def parking_status():
    occupied = latest_parking["total"] - latest_parking["available"]
    return jsonify({
        "available": latest_parking["available"],
        "occupied": occupied,
        "total": latest_parking["total"]
    })

# ================= RUN =================
if __name__ == '__main__':
    socketio.run(app, debug=True)
