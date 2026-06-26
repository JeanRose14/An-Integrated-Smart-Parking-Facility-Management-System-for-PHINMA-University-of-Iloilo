from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import secrets

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'Rose@1406')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'pk_db')
app.config['MYSQL_PORT'] = 3306

mysql = MySQL(app)

latest_parking = {"available": 5, "total": 5}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def landing_page():
    return render_template('intro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, full_name, password FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['user_email'] = email
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'Student')

        if not full_name or not email or not password:
            flash("All fields are required", "danger")
            return render_template('register.html')

        if password != confirm:
            flash("Passwords do not match", "danger")
            return render_template('register.html')

        hashed = generate_password_hash(password)

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO users (full_name, email, password, role, date_registered, expiration_date)
                VALUES (%s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY))
            """, (full_name, email, hashed, role))
            mysql.connection.commit()

            cur.execute("SELECT id, full_name FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            session['user_id'] = user[0]
            session['user_email'] = email
            session['user_name'] = user[1]
        except Exception:
            mysql.connection.rollback()
            flash("Email already registered", "danger")
            return render_template('register.html')
        finally:
            cur.close()

        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
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

    cur.close()
    latest_parking["available"] = available

    return render_template('dashboard.html',
        available=available, occupied=occupied, total=total,
        last_scan_in=last_scan_in, last_scan_out=last_scan_out,
        user_name=session.get('user_name', 'Admin')
    )

@app.route('/update-parking', methods=['POST'])
def update_parking():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    rfid = data.get("rfid")
    available = data.get("available")
    total = data.get("total")

    if not rfid:
        if available is not None and total is not None:
            latest_parking["available"] = available
            latest_parking["total"] = total
            occupied = total - available
            socketio.emit("parking_update", {
                "available": available, "occupied": occupied, "total": total,
                "scan_time": datetime.now().strftime("%I:%M:%S %p"), "type": "UPDATE"
            })
            return jsonify({"status": "ok", "mode": "occupancy_only"})
        return jsonify({"error": "No RFID or occupancy data"}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM parking_logs WHERE rfid=%s AND status='Inside' LIMIT 1", (rfid,))
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
            "available": latest_parking["available"], "occupied": occupied,
            "total": latest_parking["total"], "scan_time": now_time, "type": scan_type
        })
        socketio.emit("new_log", {"rfid": rfid, "time": now_time, "type": scan_type})

        print("SAVED TO DB:", rfid, scan_type)
    except Exception as e:
        print("DB ERROR:", e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok"})

@app.route("/parking_logs")
@login_required
def parking_logs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT rfid, time_in, time_out, status FROM parking_logs ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()

    logs = [{
        "rfid": r[0], "time_in": r[1],
        "time_out": r[2] if r[2] else "--", "status": r[3]
    } for r in rows]

    return render_template("parking_logs.html", logs=logs)

@app.route('/reg-user', methods=['GET', 'POST'])
@login_required
def reg_user():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').lower().strip()
        plate = request.form.get('vehicle_plate_number', '').strip()
        rfid = request.form.get('rfid', '').strip()
        role = request.form.get('role', 'Student')
        password = generate_password_hash(request.form.get('password', ''))

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM users WHERE email=%s OR rfid=%s", (email, rfid))
            if cur.fetchone():
                return "User with this email or RFID already exists!"

            cur.execute("""
                INSERT INTO users (full_name, email, vehicle_plate_number, rfid, role, password, date_registered, expiration_date)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY))
            """, (full_name, email, plate, rfid, role, password))
            mysql.connection.commit()
            cur.close()
            return "User Registered Successfully!"
        except Exception as e:
            print("ERROR:", e)
            return "Error: " + str(e)

    return render_template('reg_user.html')

@app.route("/users")
@login_required
def users():
    return render_template("users.html")

@app.route("/api/users")
@login_required
def get_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, full_name, email, rfid, vehicle_plate_number FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    return jsonify([{"id": r[0], "name": r[1], "email": r[2], "rfid": r[3], "plate": r[4]} for r in rows])

@app.route("/delete-user/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()
    socketio.emit("users_update")
    return jsonify({"status": "ok"})

@app.route("/edit-user/<int:user_id>", methods=["POST"])
@login_required
def edit_user(user_id):
    data = request.get_json()
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE users SET full_name=%s, email=%s, rfid=%s, vehicle_plate_number=%s
        WHERE id=%s
    """, (data.get("name"), data.get("email"), data.get("rfid"), data.get("plate"), user_id))
    mysql.connection.commit()
    cur.close()
    socketio.emit("users_update")
    return jsonify({"status": "ok"})

@app.route("/vehicles_inside")
@login_required
def vehicles_inside():
    cur = mysql.connection.cursor()
    cur.execute("SELECT rfid, time_in FROM parking_logs WHERE status='Inside'")
    vehicles = cur.fetchall()
    cur.close()
    return render_template("vehicles_inside.html", vehicles=vehicles)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/parking-status')
def parking_status():
    occupied = latest_parking["total"] - latest_parking["available"]
    return jsonify({
        "available": latest_parking["available"],
        "occupied": occupied,
        "total": latest_parking["total"]
    })

if __name__ == '__main__':
    socketio.run(app, debug=False)
