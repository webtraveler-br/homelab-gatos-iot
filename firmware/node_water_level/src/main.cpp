#include <Arduino.h>
#include "SensorCommunication.h"

#define NODE_NAME "node_water_level"

#define MQTT_TOPIC "sensors/nodes/water_level"
#define MQTT_PORT 1883
#define PUBLISH_INTERVAL 300000

#define PIN_TRIG 32
#define PIN_ECHO 35

unsigned long last_publish = 0;

JsonDocument doc;
SensorCommunication communication(NODE_NAME);

float read_distance() {
    digitalWrite(PIN_TRIG, LOW);
    delayMicroseconds(2);

    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);

    // A função pulseIn espera o pino ir para HIGH, mede o tempo, e espera ir para LOW
    long duration = pulseIn(PIN_ECHO, HIGH);

    // Velocidade do som = 0.034 cm/µs
    float distance = duration * 0.034 / 2;

    return distance;
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_TRIG, OUTPUT);
    pinMode(PIN_ECHO, INPUT);

    communication.setup_wifi(true);
    communication.setup_mqtt(MQTT_TOPIC, MQTT_PORT);
}

void loop() {
    communication.loop();

    // publica em intervalos de 5 minutos
    float distance;
    unsigned long now = millis();
    if (now - last_publish >= PUBLISH_INTERVAL) {
        last_publish = now;

        distance = read_distance();
        doc["distance"] = distance;
        if (communication.publish(doc)) {
            Serial.print("Distância em cm: ");
            Serial.println(distance);
        }
        else {
            Serial.println("Falha ao enviar mensagem.");
        }
    }
}