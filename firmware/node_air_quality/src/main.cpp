#include <Arduino.h>
#include "SensorCommunication.h"

#define NODE_NAME "node_air_quality"

#define MQTT_TOPIC "sensores/nodes/air_quality"
#define MQTT_PORT 1883
#define PUBLISH_INTERVAL 10000

#define PIN_MQ135_SENSOR 35
#define NUM_SAMPLES 10

unsigned long last_publish = 0;

JsonDocument doc;
SensorCommunication communication(NODE_NAME);

int filteredRead(int pin) {
    int sum = 0;
    for (int i = 0; i < NUM_SAMPLES; i++) {
        sum += analogRead(pin);
        delay(5); // pequeno intervalo entre leituras
    }
    return sum / NUM_SAMPLES;
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_MQ135_SENSOR, ANALOG);

    communication.setup_wifi(true);
    communication.setup_mqtt(MQTT_TOPIC, MQTT_PORT);
}

void loop() {
    communication.loop();

    // publica em intervalos de 10 segundos
    unsigned long now = millis();
    if (now - last_publish >= PUBLISH_INTERVAL) {
        last_publish = now;

        int filtered_value = filteredRead(PIN_MQ135_SENSOR);
        doc["toxicity"] = filtered_value;
        if (communication.publish(doc)) {
            Serial.print("Toxicidade (media): ");
            Serial.println(filtered_value);
        }
        else {
            Serial.println("Falha ao enviar mensagem.");
        }
    }
}