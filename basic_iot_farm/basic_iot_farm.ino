//Common libraries
#include <ESP8266WiFi.h>

//WiFiManager specific libraries
#include <DNSServer.h>          //Local DNS server used for redirecting all requests to the configuration portal
#include <ESP8266WebServer.h>   //Local WebServer used to serve as the configuration portal
#include <WiFiManager.h>        //Core library

//ArduinoOTA specific libraries
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

//HTTP Library
#include <ESP8266HTTPClient.h>

//Time Library
#include "time.h"
#include <TimeLib.h>
const char* ntpServer = "pool.ntp.org";
unsigned long epochTime;

bool getLocalTime(struct tm * info, uint32_t ms = 5000) {
    uint32_t start = millis();
    time_t now;
    while((millis()-start) <= ms) {
        time(&now);
        localtime_r(&now, info);
        if(info->tm_year > (2016 - 1900)){
            return true;
        }
        delay(10);
    }
    return false;
}

// Function that gets current epoch time
unsigned long getTime() {
  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    //Serial.println("Failed to obtain time");
    return(0);
  }
  time(&now);
  return now;
}


String iso_timestamp() {
  
    String year_s = String(year(epochTime));
    String month_s = String(month(epochTime));
    String day_s = String(day(epochTime));
    String hour_s = String(hour(epochTime));
    String minute_s = String(minute(epochTime));
    String second_s = String(second(epochTime));

    if (month(epochTime) < 10) {
      month_s = String("0") + month_s;
    }
    if (day(epochTime) < 10) {
      day_s = String("0") + day_s;
    }
    if (hour(epochTime) < 10) {
      hour_s = String("0") + hour_s;
    }
    if (minute(epochTime) < 10) {
      minute_s = String("0") + minute_s;
    }
    if (second(epochTime) < 10) {
      second_s = String("0") + second_s;
    }

    String timestamp_utc = year_s + String("-") + month_s + String("-") + day_s + String("T") + hour_s + String(":") + minute_s + String(":") + second_s + String("+00:00");

    return timestamp_utc;
}


#define lamp_pin D5
#define pump_pin D6

void setup()
{ 
  pinMode(lamp_pin, OUTPUT);
  pinMode(pump_pin, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);

  analogWriteFreq(40000);
  
  analogWrite(pump_pin, 0);
  analogWrite(lamp_pin, 0);
  analogWrite(LED_BUILTIN, 1023);
  
  Serial.begin(115200);
  //WiFi.disconnect();            //uncomment to clear SSID and PASSWORD from EEPROM
  WiFi.hostname("farm_host");     //uncomment to change hostname for device.  Replace XXXX with your own unique name
  WiFiManager wifiManager;             //WiFiManager local initialization
  wifiManager.setConfigPortalTimeout(60);
  
  //Attempt to get SSID and PASSWORD from EEPROM and connect to network
  //If it does not connect it creates an Access Point with the
  //Specified name
  wifiManager.autoConnect("farm_wifi");  //Replace XXXX with your own unique name

  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  
  configTime(0, 0, ntpServer);

  ArduinoOTA.begin();
  ArduinoOTA.setHostname("farm_ota");
  
}

void loop()
{ 
  ArduinoOTA.handle();
  epochTime = getTime();
  
  if (epochTime) {
    setTime(epochTime);
    Serial.println(iso_timestamp());

    String payload;

    HTTPClient http;  //Declare an object of class HTTPClient

    //int ans =  http.begin("http://lucapi.local/farm.log");//SHA-1
    int ans =  http.begin("http://192.168.0.49/farm.log");//SHA-1
    Serial.print("http begin: "); //should be 1
    Serial.println(ans);
    
    int httpCode = http.GET(); //Send the request
    Serial.print("http GET: "); //should be 200
    Serial.println(httpCode);
    
    if (httpCode > 0) {
      //Get the request response payload
      payload = http.getString();
      Serial.print("payload: ");
      //Print the response payload
      Serial.println(payload);

      int comma = 0;

      for (int i = 0; i<payload.length(); i++) {
        if (payload[i] == ',') {
          comma = i;
          break;
          }
      }
      
      String lamp_web = payload.substring(0, comma);
      String pump_web = payload.substring(comma+1, payload.length());

      int lamp_state = lamp_web.toInt();
      int pump_state = pump_web.toInt();
  
      Serial.print("lamp: ");
      Serial.println(lamp_state);

      Serial.print("pump: ");
      Serial.println(pump_state);

      analogWrite(lamp_pin, lamp_state);
      analogWrite(pump_pin, pump_state);
      analogWrite(LED_BUILTIN, 1023-lamp_state);

    }
    
    http.end();   //Close connection
    
    delay(1000);
    
  }
  else {
    delay(5000);
    Serial.println("time not aquired");
  }
  
}
