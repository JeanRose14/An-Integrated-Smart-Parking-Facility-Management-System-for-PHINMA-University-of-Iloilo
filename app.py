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

# ================= PARKING DATA =================
latest_parking = {
    "available": 10,
    "total": 10
}

# ================= LANDING PAGE =================
@app.route('/')
def landing_page():
    return render_template('intro.html')


@app.route('/intro')
def intro():
    return render_template('intro.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash("Please enter both email and password.", "danger")
                return render_template('login.html')

            email = email.lower().strip()

            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT password FROM registered WHERE email=%s",
                (email,)
            )
            user = cur.fetchone()
            cur.close()

            if user and check_password_hash(user[0], password):
                session['user_email'] = email
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))

            else:
                flash("Invalid email or password.", "danger")

        except Exception as e:
            print("Login Error:", e)
            flash("Login failed. Please try again.", "danger")

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            plate = request.form.get('vehicle_plate_number')
            password = request.form.get('password')

            if email:
                email = email.lower().strip()

            hashed_password = generate_password_hash(password)

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO registered (full_name, email, vehicle_plate_number, password)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, plate, hashed_password))

            mysql.connection.commit()
            cur.close()

            flash("Registered successfully!", "success")
            return redirect(url_for('dashboard'))

        except Exception as e:
            print("Register Error:", e)
            flash("Registration failed.", "danger")

    return render_template('register.html')


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ================= UPDATE PARKING =================
@app.route('/update-parking', methods=['POST'])
def update_parking():
    data = request.get_json()

    latest_parking["available"] = data["available"]
    latest_parking["total"] = data["total"]

    occupied = data["total"] - data["available"]

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO parking_logs (available_slots, occupied_slots, total_slots)
            VALUES (%s, %s, %s)
        """, (data["available"], occupied, data["total"]))

        mysql.connection.commit()
        cur.close()

    except Exception as e:
        print("Database log error:", e)

    # Send real-time update to frontend
    socketio.emit('parking_update', {
        "available": data["available"],
        "occupied": occupied,
        "total": data["total"]
    })

    return {"status": "ok"}


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ================= API PARKING STATUS =================
@app.route('/api/parking-status')
def parking_status():
    occupied = latest_parking["total"] - latest_parking["available"]

    return jsonify({
        "available": latest_parking["available"],
        "occupied": occupied,
        "total": latest_parking["total"]
    })


@app.route("/parking_logs")
def parking_logs():

    logs = [
        {"rfid":"89 5E 4E 07","time_in":"8:15 AM","time_out":"10:02 AM","status":"Completed"},
        {"rfid":"5B 71 0B 4F","time_in":"9:30 AM","time_out":"--","status":"Inside"},
        {"rfid":"1B 4D FD 4E","time_in":"7:55 AM","time_out":"9:10 AM","status":"Completed"}
    ]

    return render_template("parking_logs.html", logs=logs)



@app.route("/users")
def users():

    cur = mysql.connection.cursor()
    cur.execute("SELECT email, rfid FROM registered")
    users = cur.fetchall()
    cur.close()

    return render_template("users.html", users=users)


@app.route("/vehicles_inside")
def vehicles_inside():

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.rfid, p.time_in
        FROM parking_logs p
        JOIN registered r ON p.user_id = r.id
        WHERE p.time_out IS NULL
    """)
    vehicles = cur.fetchall()
    cur.close()

    return render_template("vehicles_inside.html", vehicles=vehicles)


# ================= RUN APP =================
if __name__ == '__main__':
    socketio.run(app, debug=True)