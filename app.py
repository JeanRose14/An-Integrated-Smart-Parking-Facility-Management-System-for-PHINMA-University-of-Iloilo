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
    return render_template('dashboard.html')

# ================= 🔥 RFID MAIN LOGIC =================
@app.route('/update-parking', methods=['POST'])
def update_parking():

    data = request.get_json()

    rfid = data.get("rfid")
    available = data.get("available")
    total = data.get("total")

    # ❌ STOP if no RFID
    if not rfid:
        return jsonify({"error": "No RFID"}), 400

    try:
        cur = mysql.connection.cursor()

        # 🔍 GET USER ID (optional)
        cur.execute("SELECT id FROM registered WHERE rfid=%s", (rfid,))
        user = cur.fetchone()
        user_id = user[0] if user else None

        # 🔍 CHECK IF INSIDE
        cur.execute("""
            SELECT id FROM parking_logs
            WHERE rfid=%s AND status='Inside'
            LIMIT 1
        """, (rfid,))
        existing = cur.fetchone()

        # ================= TIME IN =================
        if existing is None:
            cur.execute("""
                INSERT INTO parking_logs (user_id, rfid, time_in, status)
                VALUES (%s, %s, NOW(), 'Inside')
            """, (user_id, rfid))

        # ================= TIME OUT =================
        else:
            cur.execute("""
                UPDATE parking_logs
                SET time_out=NOW(), status='Completed'
                WHERE id=%s
            """, (existing[0],))

        mysql.connection.commit()
        cur.close()

    except Exception as e:
        print("DB ERROR:", e)

    # 🔥 UPDATE PARKING STATE
    if available is not None and total is not None:
        latest_parking["available"] = available
        latest_parking["total"] = total

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

# ================= USERS =================
@app.route("/users")
def users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT email, rfid FROM registered")
    users = cur.fetchall()
    cur.close()

    return render_template("users.html", users=users)

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