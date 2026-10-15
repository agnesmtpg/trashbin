#include <ESP32Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================= PENGATURAN PIN =================
const int servoPin = 18;  
const int trigPin = 14;   
const int echoPin = 27;   
const int soilPin = 26;   

// ================= OBJEK KOMPONEN =================
Servo servo360; 
LiquidCrystal_I2C lcd(0x27, 16, 2); 

// ================= VARIABEL & BATASAN =================
const int jarakDeteksi = 15;      
const int batasBasah = 2500;      

// WAKTU KALIBRASI SUDUT (SIMULASI 30 DERAJAT)
// Waktu diturunkan ke 85ms agar ayunan sangat pendek (sekitar 30 derajat)
const int waktuSwing = 85;       

void setup() {
  Serial.begin(115200);
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  servo360.attach(servoPin, 500, 2500); 
  // 90 = Perintah BERHENTI MUTLAK untuk Servo 360
  servo360.write(90); 
  
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Sistem Pemilah");
  lcd.setCursor(0, 1);
  lcd.print("Sampah Otomatis");
  delay(2000);
  lcd.clear();
  
  Serial.println("Sistem siap...");
}

float bacaJarak() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  float distance = duration * 0.034 / 2;
  return distance;
}

// Fungsi memutar servo dengan bukaan ~30 derajat
void pilahSampah(String tipe) {
  if (tipe == "BASAH") {
    Serial.println("Ayunan Basah -> KANAN (30 Derajat)");
    
    // 1. BUKA KATUP 30 DERAJAT KE KANAN
    servo360.write(180);           // Motor berputar ke kanan
    delay(waktuSwing);             // Menyala sangat sebentar (85ms)
    
    // 2. TAHAN POSISI
    servo360.write(90);            // Hentikan motor agar katup tertahan miring
    delay(2000);                   // Beri waktu 2 detik agar sampah meluncur turun
    
    // 3. KEMBALIKAN KE TENGAH
    servo360.write(0);             // Motor berputar ke kiri untuk kembali
    delay(waktuSwing);             // Waktu kembali (85ms)
  } 
  else if (tipe == "KERING") {
    Serial.println("Ayunan Kering -> KIRI (30 Derajat)");
    
    // 1. BUKA KATUP 30 DERAJAT KE KIRI
    servo360.write(0);             // Motor berputar ke kiri
    delay(waktuSwing);             // Menyala sangat sebentar (85ms)
    
    // 2. TAHAN POSISI
    servo360.write(90);            // Hentikan motor
    delay(2000);                   
    
    // 3. KEMBALIKAN KE TENGAH
    servo360.write(180);           // Motor berputar ke kanan untuk kembali
    delay(waktuSwing);             
  }
  
  // Pastikan motor terkunci diam di posisi tengah
  servo360.write(90); 
}

void loop() {
  float jarak = bacaJarak();
  
  if (jarak > 0 && jarak <= jarakDeteksi) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sampah Masuk...");
    
    delay(1500); // Tunggu sampah menyentuh plat sensor
    
    int kelembaban = analogRead(soilPin);
    Serial.print("Nilai Kelembaban: ");
    Serial.println(kelembaban);
    
    lcd.setCursor(0, 1);
    if (kelembaban < batasBasah) {
      lcd.print("Tipe: BASAH   ");
      pilahSampah("BASAH");
    } else {
      lcd.print("Tipe: KERING  ");
      pilahSampah("KERING");
    }
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Selesai Memilah");
    delay(2000); 
    lcd.clear();
  } 
  else {
    lcd.setCursor(0, 0);
    lcd.print("Menunggu Sampah ");
    lcd.setCursor(0, 1);
    lcd.print("Jarak: ");
    lcd.print(jarak, 1);
    lcd.print(" cm   ");
    delay(250); 
  }
}