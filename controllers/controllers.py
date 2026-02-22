from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import *
from flask_mysqldb import MySQL

def app_routes(app, mysql):

    @app.route('/')
    def index():
        return "RFID Backend Running"

    @app.route('/api/rfid', methods=['POST'])
    def api_rfid():
        data = request.get_json()
        uid = data.get('uid')
        insert_rfid(mysql, uid)
        return {"message": "RFID saved"}, 200

    @app.route('/rfid-logs')
    def rfid_logs():
        logs = get_all_rfid_logs(mysql)
        return render_template('test.html', logs=logs)


# from flask import render_template, request, redirect, session
# from models.models import *
# from flask_bcrypt import check_password_hash

# def app_routes(app, mysql):
#     app.secret_key = "your_secret_key"

#     @app.route('/')
#     def index():
#         users = get_all_users(mysql)
#         return render_template('index.html', users=users, edit_user=None)
    
#     @app.route('/registration')
#     def registration():
#         users = get_all_users(mysql)
#         return render_template('registration.html', users=users, edit_user=None)
    
#     @app.route('/home')
#     def home():
#         users = get_all_users(mysql)
#         return render_template('home.html', users=users, edit_user=None)
    
#     # ✅ Logout
#     @app.route('/logout')
#     def logout():
#         return redirect('/')
    
#     # ✅ Register
#     @app.route('/register', methods=['POST'])
#     def register():
#         register_user(mysql, request.form['name'], request.form['email'], request.form['password'], request.form['phone_number'])
#         return redirect('/registration')
    
#     # ✅ Login
#     @app.route('/login', methods=['GET', 'POST'])
#     def login():
#         if request.method == 'POST':
#             email = request.form['email']
#             password = request.form['password']
            
#             user = get_user_by_email(mysql, email)
#             if user:
#                 stored_password = user[3]
#                 if check_password_hash(stored_password, password):
#                     session['user_id'] = user[0]
#                     session['email'] = user[1]
#                     return redirect('/home')
#                 else:
#                     return "Email or password does not match!"
#             else:
#                 return "Email or password does not match!"
        
#         return render_template('index.html')


    # @app.route('/add', methods=['POST'])
    # def add_user_route():
    #     create_user(mysql, request.form['name'], request.form['email'], request.form['password'], request.form['phone_number'])
    #     return redirect('/user_table')

    # @app.route('/delete/<int:user_id>')
    # def delete_user_route(user_id):
    #     delete_user(mysql, user_id)
    #     return redirect('/user_table')

    # @app.route('/edit/<int:user_id>')
    # def edit_user_route(user_id):
    #     edit_user = get_user_by_id(mysql, user_id)
    #     users = get_all_users(mysql)
    #     return render_template('user_table.html', users=users, edit_user=edit_user)

    # @app.route('/update/<int:user_id>', methods=['POST'])
    # def update_user_route(user_id):
    #     update_user(mysql, user_id, request.form['name'], request.form['email'])
    #     return redirect('/user_table')
