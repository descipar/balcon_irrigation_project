#include <Arduino.h>
// Library for AZ Oled 1.3 Display
#include <U8g2lib.h>
//#ifdef U8X8_HAVE_HW_SPI
//#include <SPI.h>
//#endif
#ifdef U8X8_HAVE_HW_I2C
#include <Wire.h>
#endif


//setting uo oled display
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
//u8g2_uint_t offset;
//u8g2_uint_t width;

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

// delay between measuring. 1000 = 1s. the more measuring the more power is drawn
int waitingTime = 1000;

//Time how long the pump is turned on
int pumpTime = 3000;


//String sensorValue = "A0";
//String sensorText = "Sensor : ";
//String completeText = "complete";

String sensorValue, sensorText, completeText, pumpOn, pumpOff;

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

  // display
  //u8g2.begin();

  // string setup
  sensorValue = String();
  sensorText = String();
  completeText = String();
  pumpOn = String("pumping");
  pumpOff = String("not pumping");

}
      
void loop() {
  //display
  

  //delay until the sensors can settle in. Capacity sensor are slowzu Beginn
  delay(waitingTime);

  //measuring
  currentPlant0 = analogRead(sensorPlant0Pin);
  sensorValue = String(currentPlant0);
  sensorText = "Sensor 0: ";
  completeText = sensorText + sensorValue;

  //... output for the serial port
  Serial.print("complete wert: ");
  Serial.print(completeText);
  Serial.print("\t");   
  Serial.println("\t");   

  //...condition to pump
  if(currentPlant0 > goalPlant0) 
    {
      Wire.end();
      u8g2.begin();
      u8g2.firstPage();   
      do 
      {
        u8g2.setFont(u8g2_font_ncenB14_tr);
        u8g2.setCursor(0, 30);
        u8g2.print(completeText);
        u8g2.setCursor(0, 50);
        u8g2.print(pumpOn);
      } while ( u8g2.nextPage() );
      digitalWrite(pumpPlant0Pin, HIGH);
      Serial.print("Sensor 0 dry - pumping");
      Serial.print("\t");
      Serial.print("\t");
      delay(pumpTime);
      digitalWrite(pumpPlant0Pin, LOW);
      u8g2.clear();
      Wire.begin();

    } 
  else {
    Serial.print("iggfgfgfgc");
    Serial.print("\t");
    Serial.print("\t");
    }

  sensorValue = String();
  sensorText = String();
  completeText = String();
  
    
delay(waitingTime);
}