#include <Arduino.h>
// Library for AZ Oled 1.3 Display
#include <U8g2lib.h>

U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
u8g2_uint_t offset;
u8g2_uint_t width;

// Where are the sensors connected
int sensorPlant0Pin = A0;
int sensorPlant1Pin = A1;
//int sensorPlant2Pin = A2;
//int sensorPlant3Pin = A3;

// where are the pumps connected
int pumpPlant0Pin = 10;
int pumpPlant1Pin = 11;
//int pumpPlant2Pin = 12;
//int pumpPlant3Pin = 13;

//Below those number there is no waterflow. The higher our reading the more dry our soil is
int goalPlant0 = 300;
int goalPlant1 = 300;
//int sollTopf2 = 300;
//int sollTopf3 = 300;

int currentPlant0 = 700;
int currentPlant1 = 700;
//int istTopf2 = 700;
//int istTopf3 = 700;

// delay between measuring. 1000 = 1s. the more measuring the more power is drawn
int waitingTime = 20000;

//Time how long the pump is turned on
int pumpTime = 3000;

void setup() {
  
  //All sensors are input
  pinMode(sensorPlant0Pin, INPUT);
  pinMode(sensorPlant1Pin, INPUT);
  //pinMode(sensorPlant2Pin, INPUT);
  //pinMode(sensorPlant3Pin, INPUT);

  //all pumps are output
  pinMode(pumpPlant0Pin, OUTPUT);
  pinMode(pumpPlant1Pin, OUTPUT);
  //pinMode(pumpPlant2Pin, OUTPUT);
  //pinMode(pumpPlant3Pin, OUTPUT);


  //pumps off at the beginning
  digitalWrite(pumpPlant0Pin,LOW);
  digitalWrite(pumpPlant1Pin,LOW);
  //digitalWrite(pumpPlant2Pin,LOW);
  //digitalWrite(pumpPlant3Pin,LOW);;
  
  Serial.begin(9600);
  
}
      
void loop() {
  //Wartezeit für die Senoren zu Beginn
  delay(waitingTime);

  //Messen...
  currentPlant0 = analogRead(sensorPlant0Pin);
  currentPlant1 = analogRead(sensorPlant1Pin);
  
  //... Werte seriell ausgeben...
  Serial.print("Wasser Topf 1: ");
  Serial.print(currentPlant0);
  Serial.print("\t");   
  Serial.println("\t");   

  //...und bei Bedarf pumpen
  if(currentPlant0 > goalPlant0) 
    {
      digitalWrite(pumpPlant0Pin, HIGH);
      Serial.print("Topf1 zu trocken!!!"   );
      Serial.print("\t");
      Serial.print("\t");
      delay(pumpTime);
      digitalWrite(pumpPlant0Pin, LOW);
    } 
  else
    {
      Serial.print("Topf1 ist ok!"); 
      Serial.print("\t");
      Serial.print("\t");
    }
    
delay(waitingTime);
}