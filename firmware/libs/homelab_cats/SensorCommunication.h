#ifndef SENSOR_COMMUNICATION_H
#define SENSOR_COMMUNICATION_H

#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

class SensorCommunication {
private:
    const char* _node_name;
    char _mqtt_server_ip[40];
    const char* _topic_publish;
    int _mqtt_port;

    WiFiClient _esp_client;
    WiFiManager _wm;
    PubSubClient _client;

    void reconnect();
public:
    SensorCommunication(const char* node_name);
    void setup_wifi(bool reset_settings);
    void setup_mqtt(const char* topic_publish, int port = 1883);
    void loop();
    bool publish(JsonDocument& doc);
};

#endif // SENSOR_COMMUNICATION_H