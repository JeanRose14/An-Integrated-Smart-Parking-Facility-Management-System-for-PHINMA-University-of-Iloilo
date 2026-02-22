def insert_rfid(mysql, uid):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO rfid_logs (uid) VALUES (%s)", (uid,))
    mysql.connection.commit()
    cur.close()

def get_all_rfid_logs(mysql):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM rfid_logs ORDER BY id DESC")
    logs = cur.fetchall()
    cur.close()
    return logs



# from flask_bcrypt import Bcrypt

# def get_all_users(mysql):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM users")
#     users = cur.fetchall()
#     cur.close()
#     return users

# def get_user_by_id(mysql, user_id):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
#     user = cur.fetchone()
#     cur.close()
#     return user

# bcrypt = Bcrypt()

# def save_student_profile(mysql, fullname, student_number, email, year_level, program):
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         INSERT INTO student_profiles (fullname, student_number, email, year_level, program)
#         VALUES (%s, %s, %s, %s, %s)
#     """, (fullname, student_number, email, year_level, program))
#     mysql.connection.commit()
#     cur.close()

# def create_user(mysql, name, email, password, phone_number):
#     cur = mysql.connection.cursor()
#     hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
#     cur.execute("INSERT INTO users (name, email, password, phone_number) VALUES (%s, %s, %s, %s)", (name, email, hashed_pw, phone_number))
#     mysql.connection.commit()
#     cur.close()

# def update_user(mysql, user_id, name, email):
#     cur = mysql.connection.cursor()
#     cur.execute("UPDATE users SET name=%s, email=%s WHERE id=%s", (name, email, user_id))
#     mysql.connection.commit()
#     cur.close()

#    def delete_user(mysql, user_id):
#     cur = mysql.connection.cursor()
#     cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
#     mysql.connection.commit()
#     cur.close()
