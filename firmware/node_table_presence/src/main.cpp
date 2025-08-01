#include <Arduino.h>
#include "SensorCommunication.h"

#define NODE_NAME "node_table_presence"

#define MQTT_TOPIC "sensores/nodes/table_presence"
#define MQTT_PORT 1883

#define PIN_HEAT_SENSOR 27

bool detected = false;

JsonDocument doc;
SensorCommunication communication(NODE_NAME);

void setup() {
    Serial.begin(115200);
    pinMode(PIN_HEAT_SENSOR, INPUT);

    communication.setup_wifi(true);
    communication.setup_mqtt(MQTT_TOPIC, MQTT_PORT);
}

void loop() {
    communication.loop();
    
    bool sensor_value = digitalRead(PIN_HEAT_SENSOR) == HIGH;

    // Publica mensagem apenas quando o valor de presença mudar
    if (sensor_value != detected) {
        detected = sensor_value;
        doc["presence"] = detected;
        
        if (communication.publish(doc)) {
            Serial.println(detected ? "Detectado!" : "Nenhuma leitura.");
        } else {
            Serial.println("Falha ao enviar mensagem.");
        }
    }
}