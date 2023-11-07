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




void setup()
{
  Serial.begin(115200);
  //WiFi.disconnect();            //uncomment to clear SSID and PASSWORD from EEPROM
  WiFi.hostname("farm_host");     //uncomment to change hostname for device.  Replace XXXX with your own unique name
  WiFiManager wifiManager;             //WiFiManager local initialization
  wifiManager.setConfigPortalTimeout(10);
  
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
    delay(1000);
  }
  else {
    Serial.println("time not aquired");
    delay(5000);
  }
  
  
}
