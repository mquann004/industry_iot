#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include "DHT.h"
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"
#include <time.h>

// ================= WIFI + FIREBASE =================
#define WIFI_SSID "TEN_WIFI"
#define WIFI_PASSWORD "MAT_KHAU_WIFI"

#define API_KEY "WEB_API_KEY_CUA_FIREBASE"
#define DATABASE_URL "https://ten-project-default-rtdb.asia-southeast1.firebasedatabase.app/"

// ================= KHAI BÁO CHÂN =================
#define MQ2_PIN 34

#define GAS_BUZZER_PIN 25
#define GAS_LED_PIN 26

#define DHTPIN 4
#define DHTTYPE DHT11

#define DHT_BUZZER_PIN 27
#define DHT_LED_PIN 14

DHT dht(DHTPIN, DHTTYPE);

// ================= FIREBASE OBJECT =================
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

bool signupOK = false;

// ================= NGƯỠNG MẶC ĐỊNH =================
int gasThreshold = 400;
float tempThreshold = 34.0;
float humidityThreshold = 80.0;

// ================= BIẾN DỮ LIỆU CẢM BIẾN =================
float temperature = 0;
float humidity = 0;
int gasADC = 0;
float gasVoltage = 0;
int gasPPM = 0;

bool gasAlert = false;
bool dhtAlert = false;

// ================= CÒI GAS TÍT TÍT =================
unsigned long previousGasBuzzerTime = 0;
bool gasBuzzerState = false;
int gasBeepInterval = 200;

// ================= TIMER =================
unsigned long previousSensorReadTime = 0;
unsigned long previousFirebaseLatestTime = 0;
unsigned long previousFirebaseHistoryTime = 0;
unsigned long previousSettingsReadTime = 0;

const unsigned long SENSOR_READ_INTERVAL = 2000;       // DHT11 nên đọc mỗi 2 giây
const unsigned long FIREBASE_LATEST_INTERVAL = 5000;   // Gửi latest mỗi 5 giây
const unsigned long FIREBASE_HISTORY_INTERVAL = 60000; // Lưu history mỗi 60 giây
const unsigned long SETTINGS_READ_INTERVAL = 10000;    // Đọc settings mỗi 10 giây

String devicePath = "/devices/esp32_01";

// ================= SETUP =================
void setup() {
  Serial.begin(115200);

  dht.begin();

  analogReadResolution(12);
  analogSetPinAttenuation(MQ2_PIN, ADC_11db);

  pinMode(GAS_BUZZER_PIN, OUTPUT);
  pinMode(GAS_LED_PIN, OUTPUT);

  pinMode(DHT_BUZZER_PIN, OUTPUT);
  pinMode(DHT_LED_PIN, OUTPUT);

  // Buzzer của bạn: HIGH = im, LOW = kêu
  digitalWrite(GAS_BUZZER_PIN, HIGH);
  digitalWrite(DHT_BUZZER_PIN, HIGH);

  digitalWrite(GAS_LED_PIN, LOW);
  digitalWrite(DHT_LED_PIN, LOW);

  connectWiFi();
  setupTime();
  setupFirebase();

  Serial.println("He thong ESP32 + DHT11 + MQ2 + Firebase da san sang.");
}

// ================= LOOP =================
void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousSensorReadTime >= SENSOR_READ_INTERVAL) {
    previousSensorReadTime = currentMillis;
    readSensors();
    checkAlerts();
    printSensorData();
  }

  handleGasAlarm();
  handleDHTAlarm();

  if (Firebase.ready() && signupOK) {
    if (currentMillis - previousSettingsReadTime >= SETTINGS_READ_INTERVAL) {
      previousSettingsReadTime = currentMillis;
      readSettingsFromFirebase();
    }

    if (currentMillis - previousFirebaseLatestTime >= FIREBASE_LATEST_INTERVAL) {
      previousFirebaseLatestTime = currentMillis;
      sendLatestToFirebase();
    }

    if (currentMillis - previousFirebaseHistoryTime >= FIREBASE_HISTORY_INTERVAL) {
      previousFirebaseHistoryTime = currentMillis;
      sendHistoryToFirebase();
    }
  }
}

// ================= KẾT NỐI WIFI =================
void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Dang ket noi WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  Serial.println();
  Serial.print("Da ket noi WiFi. IP: ");
  Serial.println(WiFi.localIP());
}

// ================= CẤU HÌNH THỜI GIAN =================
void setupTime() {
  configTime(7 * 3600, 0, "pool.ntp.org", "time.nist.gov");

  Serial.print("Dang dong bo thoi gian");

  time_t now = time(nullptr);
  while (now < 100000) {
    Serial.print(".");
    delay(500);
    now = time(nullptr);
  }

  Serial.println();
  Serial.println("Da dong bo thoi gian.");
}

// ================= CẤU HÌNH FIREBASE =================
void setupFirebase() {
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;

  if (Firebase.signUp(&config, &auth, "", "")) {
    Serial.println("Dang nhap Firebase Anonymous thanh cong.");
    signupOK = true;
  } else {
    Serial.print("Loi dang nhap Firebase: ");
    Serial.println(config.signer.signupError.message.c_str());
  }

  config.token_status_callback = tokenStatusCallback;

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  createDefaultSettingsIfNeeded();
}

// ================= TẠO SETTINGS MẶC ĐỊNH =================
void createDefaultSettingsIfNeeded() {
  String path = devicePath + "/settings";

  if (!Firebase.RTDB.getJSON(&fbdo, path)) {
    FirebaseJson json;

    json.set("temp_threshold", tempThreshold);
    json.set("humidity_threshold", humidityThreshold);
    json.set("gas_threshold", gasThreshold);

    if (Firebase.RTDB.setJSON(&fbdo, path, &json)) {
      Serial.println("Da tao settings mac dinh tren Firebase.");
    } else {
      Serial.print("Loi tao settings: ");
      Serial.println(fbdo.errorReason());
    }
  }
}

// ================= ĐỌC CẢM BIẾN =================
void readSensors() {
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Loi: Khong doc duoc DHT11.");
    dhtAlert = false;
    return;
  }

  gasADC = analogRead(MQ2_PIN);
  gasVoltage = gasADC * (3.3 / 4095.0);
  gasPPM = map(gasADC, 0, 4095, 0, 1000);
}

// ================= KIỂM TRA CẢNH BÁO =================
void checkAlerts() {
  gasAlert = gasPPM >= gasThreshold;
  dhtAlert = temperature >= tempThreshold || humidity >= humidityThreshold;
}

// ================= IN SERIAL =================
void printSensorData() {
  Serial.println("----------------------------------");

  Serial.print("Nhiet do: ");
  Serial.print(temperature);
  Serial.print(" C");

  Serial.print(" | Do am: ");
  Serial.print(humidity);
  Serial.print(" %");

  Serial.print(" | Gas ADC: ");
  Serial.print(gasADC);

  Serial.print(" | Gas Voltage: ");
  Serial.print(gasVoltage);
  Serial.print(" V");

  Serial.print(" | Gas PPM: ");
  Serial.print(gasPPM);
  Serial.print(" ppm");

  Serial.print(" | Gas Alert: ");
  Serial.print(gasAlert ? "CO" : "KHONG");

  Serial.print(" | DHT Alert: ");
  Serial.println(dhtAlert ? "CO" : "KHONG");
}

// ================= GỬI LATEST LÊN FIREBASE =================
void sendLatestToFirebase() {
  FirebaseJson json;

  unsigned long timestamp = getUnixTime();

  json.set("temperature", temperature);
  json.set("humidity", humidity);
  json.set("gas_adc", gasADC);
  json.set("gas_voltage", gasVoltage);
  json.set("gas_ppm", gasPPM);
  json.set("gas_alert", gasAlert);
  json.set("dht_alert", dhtAlert);
  json.set("timestamp", timestamp);

  String path = devicePath + "/latest";

  if (Firebase.RTDB.setJSON(&fbdo, path, &json)) {
    Serial.println("Da gui latest len Firebase.");
  } else {
    Serial.print("Loi gui latest: ");
    Serial.println(fbdo.errorReason());
  }
}

// ================= GỬI HISTORY LÊN FIREBASE =================
void sendHistoryToFirebase() {
  FirebaseJson json;

  unsigned long timestamp = getUnixTime();

  json.set("temperature", temperature);
  json.set("humidity", humidity);
  json.set("gas_ppm", gasPPM);
  json.set("gas_adc", gasADC);
  json.set("gas_voltage", gasVoltage);
  json.set("gas_alert", gasAlert);
  json.set("dht_alert", dhtAlert);
  json.set("timestamp", timestamp);

  String path = devicePath + "/history/" + String(timestamp);

  if (Firebase.RTDB.setJSON(&fbdo, path, &json)) {
    Serial.println("Da luu history len Firebase.");
  } else {
    Serial.print("Loi luu history: ");
    Serial.println(fbdo.errorReason());
  }
}

// ================= ĐỌC SETTINGS TỪ FIREBASE =================
void readSettingsFromFirebase() {
  String basePath = devicePath + "/settings";

  if (Firebase.RTDB.getFloat(&fbdo, basePath + "/temp_threshold")) {
    tempThreshold = fbdo.floatData();
  }

  if (Firebase.RTDB.getFloat(&fbdo, basePath + "/humidity_threshold")) {
    humidityThreshold = fbdo.floatData();
  }

  if (Firebase.RTDB.getInt(&fbdo, basePath + "/gas_threshold")) {
    gasThreshold = fbdo.intData();
  }

  Serial.print("Settings hien tai | Temp: ");
  Serial.print(tempThreshold);

  Serial.print(" | Humi: ");
  Serial.print(humidityThreshold);

  Serial.print(" | Gas: ");
  Serial.println(gasThreshold);
}

// ================= XỬ LÝ CÒI GAS TÍT TÍT =================
void handleGasAlarm() {
  if (gasAlert == true) {
    digitalWrite(GAS_LED_PIN, HIGH);

    unsigned long currentMillis = millis();

    if (currentMillis - previousGasBuzzerTime >= gasBeepInterval) {
      previousGasBuzzerTime = currentMillis;

      gasBuzzerState = !gasBuzzerState;

      if (gasBuzzerState == true) {
        digitalWrite(GAS_BUZZER_PIN, LOW);   // Còi kêu
      } else {
        digitalWrite(GAS_BUZZER_PIN, HIGH);  // Còi im
      }
    }

  } else {
    digitalWrite(GAS_BUZZER_PIN, HIGH);
    digitalWrite(GAS_LED_PIN, LOW);
    gasBuzzerState = false;
  }
}

// ================= XỬ LÝ CÒI DHT11 ÂM DÀI =================
void handleDHTAlarm() {
  if (dhtAlert == true) {
    digitalWrite(DHT_LED_PIN, HIGH);
    digitalWrite(DHT_BUZZER_PIN, LOW);     // Còi kêu âm dài
  } else {
    digitalWrite(DHT_LED_PIN, LOW);
    digitalWrite(DHT_BUZZER_PIN, HIGH);    // Còi im
  }
}

// ================= LẤY UNIX TIMESTAMP =================
unsigned long getUnixTime() {
  time_t now;
  time(&now);
  return now;
}