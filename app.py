from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.secret_key = "secretkey"

# ================= MYSQL CONFIG =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rose@1406'
app.config['MYSQL_DB'] = 'pk_db'
app.config['MYSQL_PORT'] = 3306

mysql = MySQL(app)

# ================= PARKING STATE =================
latest_parking = {
    "available": 5,
    "total": 5
}

# ================= LANDING =================
@app.route('/')
def landing_page():
    return render_template('intro.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute("SELECT password FROM registered WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[0], password):
            session['user_email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login", "danger")

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email').lower().strip()
        plate = request.form.get('vehicle_plate_number')
        password = generate_password_hash(request.form.get('password'))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO registered (full_name, email, vehicle_plate_number, password)
            VALUES (%s, %s, %s, %s)
        """, (full_name, email, plate, password))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for('dashboard'))

    return render_template('register.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    cur = mysql.connection.cursor()

    # Count vehicles currently inside
    cur.execute("SELECT COUNT(*) FROM parking_logs WHERE status='Inside'")
    occupied = cur.fetchone()[0]

    total = latest_parking["total"]
    available = total - occupied

    # Get last scan in
    cur.execute("""
        SELECT time_in FROM parking_logs
        ORDER BY time_in DESC LIMIT 1
    """)
    last_in = cur.fetchone()
    last_scan_in = last_in[0].strftime("%I:%M:%S %p") if last_in and last_in[0] else "--"

    # Get last scan out
    cur.execute("""
        SELECT time_out FROM parking_logs
        WHERE time_out IS NOT NULL
        ORDER BY time_out DESC LIMIT 1
    """)
    last_out = cur.fetchone()
    last_scan_out = last_out[0].strftime("%I:%M:%S %p") if last_out and last_out[0] else "--"

    cur.close()

    # Keep in-memory state in sync
    latest_parking["available"] = available

    return render_template('dashboard.html',
        available=available,
        occupied=occupied,
        total=total,
        last_scan_in=last_scan_in,
        last_scan_out=last_scan_out
    )

# ================= 🔥 RFID MAIN LOGIC =================
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

        # 🔍 CHECK IF ALREADY INSIDE
        cur.execute("""
            SELECT id FROM parking_logs
            WHERE rfid=%s AND status='Inside'
            LIMIT 1
        """, (rfid,))
        existing = cur.fetchone()

        # ================= TIME IN =================
        if existing is None:
            cur.execute("""
                INSERT INTO parking_logs (rfid, time_in, status)
                VALUES (%s, NOW(), 'Inside')
            """, (rfid,))
            scan_type = "IN"

            cur.execute("""
                SELECT time_in FROM parking_logs
                ORDER BY id DESC LIMIT 1
            """)

        # ================= TIME OUT =================
        else:
            cur.execute("""
                UPDATE parking_logs
                SET time_out=NOW(), status='Completed'
                WHERE id=%s
            """, (existing[0],))
            scan_type = "OUT"

            cur.execute("""
                SELECT time_out FROM parking_logs
                ORDER BY id DESC LIMIT 1
            """)

        result = cur.fetchone()

        mysql.connection.commit()
        cur.close()

        now_time = result[0].strftime("%I:%M:%S %p") if result else "--"

        # 🔥 UPDATE STATE
        if available is not None and total is not None:
            latest_parking["available"] = available
            latest_parking["total"] = total

        occupied = latest_parking["total"] - latest_parking["available"]

        # 🔥 SINGLE EMIT
        socketio.emit("parking_update", {
            "available": latest_parking["available"],
            "occupied": occupied,
            "total": latest_parking["total"],
            "scan_time": now_time,
            "type": scan_type
        })

        # 🔥 ADD THIS (AUTO UPDATE PARKING LOGS PAGE)
        socketio.emit("new_log", {
            "rfid": rfid,
            "time": now_time,
            "type": scan_type
        })

        print("✅ SAVED TO DB:", rfid, scan_type)

    except Exception as e:
        print("❌ DB ERROR:", e)

    return jsonify({"status": "ok"})

# ================= PARKING LOGS PAGE =================
@app.route("/parking_logs")
def parking_logs():

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT rfid, time_in, time_out, status
        FROM parking_logs
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    cur.close()

    logs = []
    for row in rows:
        logs.append({
            "rfid": row[0],
            "time_in": row[1],
            "time_out": row[2] if row[2] else "--",
            "status": row[3]
        })

    return render_template("parking_logs.html", logs=logs)

# ================= REGISTRATION FOR USERS =================
@app.route('/reg-user', methods=['GET', 'POST'])
def reg_user():

    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta

        full_name = request.form.get('full_name')
        email = request.form.get('email')
        plate = request.form.get('vehicle_plate_number')
        rfid = request.form.get('rfid')
        role = request.form.get('role')
        password = generate_password_hash(request.form.get('password'))

        date_registered = datetime.now()
        expiration_date = date_registered + timedelta(days=30)  # 30 days validity

        try:
            cur = mysql.connection.cursor()

            # check duplicate
            cur.execute("SELECT id FROM users WHERE email=%s OR rfid=%s", (email, rfid))
            if cur.fetchone():
                return "User already exists!"

            cur.execute("""
                INSERT INTO users 
                (full_name, email, vehicle_plate_number, rfid, role, password, date_registered, expiration_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (full_name, email, plate, rfid, role, password, date_registered, expiration_date))

            mysql.connection.commit()
            cur.close()

            return "User Registered Successfully!"

        except Exception as e:
            print("ERROR:", e)
            return "Error"

    return render_template('reg_user.html')

# ================= USERS PAGE =================
@app.route("/users")
def users():
    # simple render lang (no data needed)
    return render_template("users.html")


# ================= API GET USERS =================
@app.route("/api/users")
def get_users():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, full_name, email, rfid, vehicle_plate_number
        FROM registered
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    cur.close()

    users = []
    for r in rows:
        users.append({
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "rfid": r[3],
            "plate": r[4]
        })

    return jsonify(users)


# ================= DELETE USER =================
@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM registered WHERE id=%s", (user_id,))

    mysql.connection.commit()
    cur.close()

    # 🔥 AUTO UPDATE FRONTEND
    socketio.emit("users_update")

    return jsonify({"status": "ok"})


# ================= EDIT USER =================
@app.route("/edit-user/<int:user_id>", methods=["POST"])
def edit_user(user_id):
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    rfid = data.get("rfid")
    plate = data.get("plate")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE registered
        SET full_name=%s, email=%s, rfid=%s, vehicle_plate_number=%s
        WHERE id=%s
    """, (name, email, rfid, plate, user_id))

    mysql.connection.commit()
    cur.close()

    # 🔥 AUTO UPDATE FRONTEND
    socketio.emit("users_update")

    return jsonify({"status": "ok"})

# ================= VEHICLES INSIDE =================
@app.route("/vehicles_inside")
def vehicles_inside():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT rfid, time_in
        FROM parking_logs
        WHERE status='Inside'
    """)
    vehicles = cur.fetchall()
    cur.close()

    return render_template("vehicles_inside.html", vehicles=vehicles)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
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