# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import Error
import serial
import time
import threading

# 设置串口
SERIAL_PORT = "COM1"  # 替换为 Arduino 实际的串口号
BAUD_RATE = 9600

# 连接到串口
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, 8, timeout=1)

app = Flask(__name__)


# 数据库连接配置
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # 替换为数据库用户名
            password='123456',  # 替换为数据库密码
            database='qianru'  # 替换为数据库名
        )
        if connection.is_connected():
            print("Connected to MySQL database")
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None


# 插入数据到数据库
def insert_data(connection, temperature, distance, is_room_occupied, someone_at_door, is_outroom):
    cursor = connection.cursor()
    sql_query = """
    INSERT INTO sensor_data (temperature, distance, is_room_occupied, someone_at_door, is_outroom, timestamp)
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    data_tuple = (temperature, distance, is_room_occupied, someone_at_door, is_outroom)
    cursor.execute(sql_query, data_tuple)
    connection.commit()
    print(f"Data inserted: {data_tuple}")


# 处理和存储串口数据
def chuankoushuju():
    connection = create_connection()
    if connection is None:
        print("Failed to connect to database.")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                # 读取一行并解码
                line = ser.readline().decode('utf-8').strip()
                print(f"Received data: {line}")

                # 解析数据
                parts = line.split(", ")
                if len(parts) == 5:
                    temperature = float(parts[0].split(": ")[1].replace("C", "").strip())
                    distance = float(parts[1].split(": ")[1].replace("cm", "").strip())
                    is_room_occupied = parts[2].split(": ")[1].strip() == "Yes"
                    someone_at_door = parts[3].split(": ")[1].strip() == "Yes"
                    is_outroom = parts[4].split(": ")[1].strip() == "Yes"

                    # 插入数据到数据库
                    insert_data(connection, temperature, distance, is_room_occupied, someone_at_door, is_outroom)

                time.sleep(1)  # 防止过快读取

    except KeyboardInterrupt:
        print("Program interrupted")
    finally:
        if connection.is_connected():
            connection.close()
        ser.close()


# 获取最新的传感器数据
def get_latest_sensor_data():
    connection = create_connection()
    if connection is None:
        return None
    cursor = connection.cursor(dictionary=True)
    sql = "SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1"
    cursor.execute(sql)
    data = cursor.fetchone()
    connection.close()
    return data


# 路由：返回最新传感器数据
@app.route('/get_sensor_data')
def get_sensor_data():
    data = get_latest_sensor_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Failed to retrieve data"}), 500


@app.route('/')
def index():
    return redirect(url_for('user_login'))


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        if username == '' or password == '':
            js_code = "<script>alert('请输入账号密码！'); history.back();</script>"
            return js_code

        user = get_user_by_username(username)
        if user:
            js_code = "<script>alert('用户已存在！'); history.back();</script>"
            return js_code
        else:
            register_db(username, password)
            return redirect(url_for('user_login'))


def register_db(username, password):
    db = create_connection()
    if db is None:
        return "<script>alert('数据库连接失败！'); history.back();</script>"
    cursor = db.cursor()
    sql = "INSERT INTO user (username, password) VALUES (%s, %s)"
    cursor.execute(sql, (username, password))
    db.commit()
    db.close()


def get_user_by_username(username):
    db = create_connection()
    if db is None:
        return None
    cursor = db.cursor(dictionary=True)
    sql = "SELECT * FROM user WHERE username = %s"
    cursor.execute(sql, (username,))
    user = cursor.fetchone()
    db.close()
    return user


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            js_code = "<script>alert('请输入账号密码！'); history.back();</script>"
            return js_code

        user = get_user_by_username(username)
        if user and user['password'] == password:
            return redirect(url_for('admin'))
        else:
            js_code = "<script>alert('登录失败！'); history.back();</script>"
            return js_code


if __name__ == '__main__':
    # 在后台启动串口数据读取
    thread = threading.Thread(target=chuankoushuju)
    thread.daemon = True  # 使线程在主线程退出时也能退出
    thread.start()

    # 启动Flask应用
    app.run('127.0.0.1', 5002, debug=True)
