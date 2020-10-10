#include <Arduino.h>

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
int goalPlant0 = 350;
int goalPlant1 = 350;
//int sollTopf2 = 300;
//int sollTopf3 = 300;

int currentPlant0 = 700;
int currentPlant1 = 700;
//int istTopf2 = 700;
//int istTopf3 = 700;

// delay between measuring. 1000 = 1s. the more measuring the more power is drawn. 
// delays under 30000 do not seem to work as the sensors delivers wrong value
int waitingTime = 30000;

//Time how long the pump is turned on f
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
  //delay until the sensors can settle in. Capacity sensor are slow at the beginning
  delay(waitingTime);
  currentPlant0 = 0;
  currentPlant1 = 0;
  //measuring
  currentPlant0 = analogRead(sensorPlant0Pin);
  currentPlant1 = analogRead(sensorPlant1Pin);

  //... output for the serial port
  Serial.print("Sensor 0: ");
  Serial.print(currentPlant0);
  Serial.print("\t");   
  Serial.println("\t");   

  //...condition to pump
  if(currentPlant0 > goalPlant0) 
    {
      Serial.print("Sensor 0 dry - pumping");
      Serial.print("\t");
      Serial.println("\t");
      digitalWrite(pumpPlant0Pin, HIGH);
      delay(pumpTime);
      digitalWrite(pumpPlant0Pin, LOW);
    } 
  else 
    {
    Serial.print("Sensor 0 is wet enough");
    Serial.print("\t");
    Serial.println("\t");
    }
  
  //measuring
  Serial.println("Next Sensor");


  //... output for the serial port
  
  Serial.print("Sensor 1: ");
  Serial.print(currentPlant1);
  Serial.print("\t");   
  Serial.println("\t");

  if(currentPlant1 > goalPlant1) 
    {
      Serial.print("Sensor 1 dry - pumping");
      Serial.print("\t");
      Serial.println("\t");
      digitalWrite(pumpPlant1Pin, HIGH);
      delay(pumpTime);
      digitalWrite(pumpPlant1Pin, LOW);
    } 
  else 
    {
    Serial.print("Sensor 1 is wet enough");
    Serial.print("\t");
    Serial.println("\t");
    }
  
  Serial.println("Loop end");

}