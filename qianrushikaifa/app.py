from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于闪现消息和会话管理

# 数据库连接配置
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',           # 替换为数据库用户名
            password='123456',      # 替换为数据库密码
            database='qianru'       # 替换为数据库名
        )
        if connection.is_connected():
            print("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# 用户登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # 检查用户是否存在
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            # 使用 session 存储用户登录状态
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))  # 重定向到登录成功后的页面
        else:
            flash("Invalid username or password", "danger")

        cursor.close()
        connection.close()

    return render_template('login.html')

# 登录成功后的页面
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in first", "danger")
        return redirect(url_for('login'))
    return f"Welcome, {session['username']}!"

# 用户注销
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
