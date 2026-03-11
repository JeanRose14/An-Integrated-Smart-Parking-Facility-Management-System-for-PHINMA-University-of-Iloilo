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

            if email:
                email = email.lower().strip()

            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT password FROM registered WHERE email=%s",
                (email,)
            )
            user = cur.fetchone()
            cur.close()

            if user and check_password_hash(user[0], password):
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "danger")

        except Exception as e:
            print("Login Error:", e)
            flash("Login failed.", "danger")

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


# ================= RUN APP =================
if __name__ == '__main__':
    socketio.run(app, debug=True)