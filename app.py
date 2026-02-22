from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = "secretkey"

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'smart_parking'

mysql = MySQL(app)


# ================= LANDING =================
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
                "SELECT * FROM registered WHERE email=%s AND password=%s",
                (email, password)
            )
            user = cur.fetchone()
            print("USER FOUND:", user)
            cur.close()

            if user:
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "danger")

        except Exception as e:
            print(f"Login Error: {e}")
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

            # clean email
            if email:
                email = email.lower().strip()

            # save to database
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO registered (full_name, email, vehicle_plate_number, password)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, plate, password))
            mysql.connection.commit()
            cur.close()

            flash("Registered successfully!", "success")

            # ✅ FIX: redirect to dashboard after register
            return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"Error: {e}")
            flash("Registration failed.", "danger")

    return render_template('register.html')


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)