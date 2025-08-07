#include <Arduino.h>
#include "SensorCommunication.h"

#define NODE_NAME "node_table_presence"

#define MQTT_TOPIC "sensors/nodes/table_presence"
#define MQTT_CMD_TOPIC "commands/nodes/table_presence"
#define MQTT_PORT 1883

#define PIN_BUZZER 26
#define PIN_HEAT_SENSOR 27

#define BUZZER_DURATION 1000 // 1 segundo

bool detected = false;

JsonDocument doc;
SensorCommunication communication(NODE_NAME);

bool buzzer_active = false;
unsigned long buzzer_start_time = 0;

void command_callback(const char* topic, const JsonDocument& cmd_doc) {
    Serial.print("Comando recebido!");

    // ativa o buzzer e começa a contagem (sem bloquear o loop)
    if (!cmd_doc["action"].isNull() && cmd_doc["action"] == "buzzer") {
        Serial.println("Ativando buzzer");
        digitalWrite(PIN_BUZZER, HIGH);
        buzzer_active = true;
        buzzer_start_time = millis();
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_HEAT_SENSOR, INPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);

    communication.setup_wifi(true);
    communication.setup_mqtt(MQTT_TOPIC, MQTT_PORT, MQTT_CMD_TOPIC, command_callback);
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
        }
        else {
            Serial.println("Falha ao enviar mensagem.");
        }
    }

    // desliga o buzzer após BUZZER_DURATION
    if (buzzer_active) {
        if (millis() - buzzer_start_time >= BUZZER_DURATION) {
            digitalWrite(PIN_BUZZER, LOW);
            buzzer_active = false;
            Serial.println("Buzzer desativado.");
        }
    }
}