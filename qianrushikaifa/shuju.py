import serial
import mysql.connector
from mysql.connector import Error
import time
from flask import Flask, request, render_template, redirect, url_for
# 设置串口
SERIAL_PORT = "COM1"  # 替换为 Arduino 实际的串口号
BAUD_RATE = 9600

# 连接到串口
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
app = Flask(__name__)

# 连接到 MySQL 数据库
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


# 数据库表结构
# 确保在数据库中创建以下表结构
# CREATE TABLE sensor_data (
#     id INT AUTO_INCREMENT PRIMARY KEY,
#     temperature FLOAT,
#     distance FLOAT,
#     is_room_occupied BOOLEAN,
#     someone_at_door BOOLEAN,
#     is_outroom BOOLEAN,
#     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );

# 检查数据是否发生变化
def is_data_changed(connection, new_data):
    cursor = connection.cursor(dictionary=True)
    # 查询最近的一条记录
    query = """
    SELECT temperature, distance, is_room_occupied, someone_at_door, is_outroom
    FROM sensor_data
    ORDER BY id DESC
    LIMIT 1
    """
    cursor.execute(query)
    last_data = cursor.fetchone()
    cursor.close()

    # 如果数据库中没有记录，直接插入
    if last_data is None:
        print("No existing records, inserting new data.")
        return True

    # 比较新数据与最后一条记录的数据
    return (
        float(new_data["temperature"]) != float(last_data["temperature"]) or
        float(new_data["distance"]) != float(last_data["distance"]) or
        new_data["is_room_occupied"] != bool(last_data["is_room_occupied"]) or
        new_data["someone_at_door"] != bool(last_data["someone_at_door"]) or
        new_data["is_outroom"] != bool(last_data["is_outroom"])
    )


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

                # 解析数据，检查格式是否正确
                parts = line.split(", ")
                if len(parts) != 5:
                    print(f"Invalid data format: {line}")
                    continue  # 跳过本次循环

                try:
                    # 解析温度
                    temperature = float(parts[0].split(":")[1].replace("C", "").strip())
                    # 解析距离
                    distance = float(parts[1].split(":")[1].replace("cm", "").strip())
                    # 特殊处理 Room Occupi
                    is_room_occupied = "Yes" in parts[2]  # 检查是否包含 Yes
                    # 解析门铃状态
                    someone_at_door = "Yes" in parts[3]
                    # 解析是否在房间外
                    is_outroom = "Yes" in parts[4]

                    new_data = {
                        "temperature": temperature,
                        "distance": distance,
                        "is_room_occupied": is_room_occupied,
                        "someone_at_door": someone_at_door,
                        "is_outroom": is_outroom,
                    }
                except (IndexError, ValueError) as e:
                    print(f"Error parsing data: {line}. Error: {e}")
                    continue  # 跳过本次循环

                # 检测数据是否发生变化
                if is_data_changed(connection, new_data):
                    # 插入数据到数据库
                    insert_data(
                        connection,
                        new_data["temperature"],
                        new_data["distance"],
                        new_data["is_room_occupied"],
                        new_data["someone_at_door"],
                        new_data["is_outroom"]
                    )
                else:
                    print("Data unchanged, not inserted.")

                time.sleep(1)  # 防止过快读取

    except KeyboardInterrupt:
        print("Program interrupted")
    finally:
        if connection.is_connected():
            connection.close()
        ser.close()


if __name__ == '__main__':
    chuankoushuju()