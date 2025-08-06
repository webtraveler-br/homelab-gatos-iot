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
    const char* _topic_subscribe;
    int _mqtt_port;
    void (*_user_callback)(const char* topic, const JsonDocument&) = nullptr;

    WiFiClient _esp_client;
    WiFiManager _wm;
    PubSubClient _client;

    void reconnect();
    void callback_json_wrapper(const char* topic, const byte* payload, unsigned int length);
public:
    SensorCommunication(const char* node_name);
    void setup_wifi(bool reset_settings);
    void setup_mqtt(const char* topic_publish, int port = 1883, const char* topic_subscribe = nullptr, void (*callback)(const char*, const JsonDocument&) = nullptr);
    void loop();
    bool publish(JsonDocument& doc);
};

#endif // SENSOR_COMMUNICATION_H