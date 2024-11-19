#include <Arduino.h>
#include <Arduino_FreeRTOS.h>
#include <queue.h>

// 引脚定义
const int lm35Pin = A2;      // LM35 温度传感器引脚
const int pirPin = 3;        // 红外传感器（用开关代替）引脚
const int relayPin = 4;      // 继电器引脚
const int ledPin = 5;        // LED 灯引脚
const int buzzerPin = 6;     // 蜂鸣器引脚
const int gp2d12Pin = A4;    // GP2D12 距离传感器引脚
const int bellPin = 7;       // 门铃引脚

// 任务句柄
TaskHandle_t TaskHandleMonitorEnvironment;
TaskHandle_t TaskHandleControlDevice;
TaskHandle_t TaskHandleMonitorDistance;
TaskHandle_t TaskHandleSerialOutput;

// 队列句柄
QueueHandle_t dataQueue;

// 变量
volatile bool isRoomOccupied = false;
float temperature = 0.0;
const int DETECTED_DISTANCE = 20;
volatile bool issomeone = false;
volatile bool isoutroom = false;
float distance =0.0;

// 数据结构，用于传输温度、距离和状态
struct SensorData {
  float temperature;
  float distance;
  bool isRoomOccupied;
  bool issomeone;
  bool isoutroom;
};

// 环境监控任务：读取温度和检测房间是否有人
void monitorEnvironment(void *pvParameters) {
  (void) pvParameters;
  pinMode(pirPin, INPUT_PULLUP);
  for (;;) {
    // 读取温度
    int sensorValue = analogRead(lm35Pin);
    temperature = sensorValue * (5.0 / 1023.0) * 100;

    // 检测房间是否有人
    isRoomOccupied = (digitalRead(pirPin) == LOW);

    // 将数据发送到队列
    SensorData data;
    data.temperature = temperature;
    data.isRoomOccupied = isRoomOccupied;
    data.isoutroom = isoutroom;
    data.distance = distance;
    data.issomeone = issomeone;
    xQueueSend(dataQueue, &data, portMAX_DELAY);

    vTaskDelay(pdMS_TO_TICKS(1000)); // 每秒读取一次
  }
}

// 控制设备（灯光或风扇）任务
void controlDevice(void *pvParameters) {
  (void) pvParameters;
  pinMode(relayPin, OUTPUT);
  pinMode(ledPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);

  for (;;) {
    if (isRoomOccupied) {
      if (temperature > 30.0) {
        digitalWrite(relayPin, HIGH); // 打开继电器
      }
      digitalWrite(ledPin, HIGH);     // 打开LED灯
    } else {
      digitalWrite(relayPin, LOW);    // 关闭继电器
      digitalWrite(ledPin, LOW);      // 关闭LED灯
    }
    if (issomeone && isoutroom) {
      analogWrite(buzzerPin, 127);    // 打开蜂鸣器并设置响度
    } else {
      analogWrite(buzzerPin, 0);      // 关闭蜂鸣器
    }

    SensorData data;
    data.issomeone = issomeone;
    data.temperature = temperature;
    data.isRoomOccupied = isRoomOccupied;
    data.isoutroom = isoutroom;
    data.distance = distance;
    xQueueSend(dataQueue, &data, portMAX_DELAY);

    vTaskDelay(pdMS_TO_TICKS(1000));  // 每秒更新一次
  }
}

// GP2D12 距离传感器的转换函数
float convertToDistance(int analogValue) {
  return 2547.8 / ((float)analogValue * 0.49 - 10.41) - 0.42;
}

// 监测 GP2D12 传感器（门口检测）任务
void monitorDistance(void *pvParameters) {
  (void) pvParameters;
  pinMode(bellPin, INPUT_PULLUP);
  for (;;) {
    int distanceValue = analogRead(gp2d12Pin);
    float actualDistance = convertToDistance(distanceValue);
    distance = actualDistance;
    isoutroom = (actualDistance < DETECTED_DISTANCE);
    issomeone = (digitalRead(bellPin) == LOW);

    SensorData data;
    data.temperature = temperature;
    data.isRoomOccupied = isRoomOccupied;
    data.isoutroom = isoutroom;
    data.distance = distance;
    data.issomeone = issomeone;
    xQueueSend(dataQueue, &data, portMAX_DELAY);

    vTaskDelay(pdMS_TO_TICKS(6000));
  }
}

// 串口发送任务
void serialOutput(void *pvParameters) {
  (void) pvParameters;
  SensorData data;
  for (;;) {
    if (xQueueReceive(dataQueue, &data, portMAX_DELAY) == pdPASS) {
      Serial.print("Temperature: ");
      Serial.print(data.temperature);
      Serial.print(" C, Distance: ");
      Serial.print(data.distance);
      Serial.print(" cm, Room Occupied: ");
      Serial.print(data.isRoomOccupied ? "Yes" : "No");
      Serial.print(", Someone ring the doorbell: ");
      Serial.print(data.issomeone ? "Yes" : "No");
      Serial.print(", Outroom: ");
      Serial.println(data.isoutroom ? "Yes" : "No");
    }
  }
}

void setup() {
  Serial.begin(9600);

  // 创建队列
  dataQueue = xQueueCreate(10, sizeof(SensorData));

  // 创建 FreeRTOS 任务
  xTaskCreate(monitorEnvironment, "MonitorEnvironment", 128, NULL, 1, &TaskHandleMonitorEnvironment);
  xTaskCreate(controlDevice, "ControlDevice", 128, NULL, 1, &TaskHandleControlDevice);
  xTaskCreate(monitorDistance, "MonitorDistance", 128, NULL, 2, &TaskHandleMonitorDistance);
  xTaskCreate(serialOutput, "SerialOutput", 128, NULL, 1, &TaskHandleSerialOutput);
}

void loop() {
  // 主循环不做任何操作，所有功能由 FreeRTOS 任务执行
}
