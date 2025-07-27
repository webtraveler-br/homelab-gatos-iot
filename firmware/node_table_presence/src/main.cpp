#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

WiFiClient espClient;
WiFiManager wm;
PubSubClient client(espClient);
JsonDocument doc;

const char* node_name = "node_table_presence";

const int pin_heat_sensor = 27;

char mqtt_server[40] = "";

const char* mqtt_topic_publish = "sensores/nodes/table_presence";
const int mqtt_port = 1883;

bool detected = false;
long lastMsg = 0;

void reconnect();
void publish(bool);

void setup() {
    Serial.begin(115200);
    pinMode(pin_heat_sensor, INPUT);

    // Descomente a linha abaixo para forçar a aparição do portal de configuração.
    // wm.resetSettings();

    // Adiciona um campo novo ao wifi manager, permitindo configurar o IP do MQTT
    WiFiManagerParameter custom_mqtt_server("server", "MQTT Server IP", mqtt_server, 40);
    wm.addParameter(&custom_mqtt_server);

    // Se o usuário não configurar em 10 minutos, o ESP reinicia.
    wm.setConfigPortalTimeout(600);

    if (!wm.autoConnect(node_name)) {
        Serial.println("Tempo limite atingido. Reiniciando...");
        ESP.restart();
    } else {
        Serial.println("Conectado!");
        Serial.print("Endereço IP: ");
        Serial.println(WiFi.localIP());
    }

    strcpy(mqtt_server, custom_mqtt_server.getValue());
    Serial.print("MQTT Server IP set to: ");
    Serial.println(mqtt_server);

    client.setServer(mqtt_server, mqtt_port);
}

void loop() {
    bool sensor_value = digitalRead(pin_heat_sensor) == HIGH;
    long now = millis();

    if (sensor_value && !detected) {
        Serial.println("Detectado!");
    } else if (!sensor_value && detected) {
        Serial.println("Nenhuma leitura.");
    }

    detected = sensor_value;

    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    // Lógica para enviar uma mensagem a cada 10 segundos (sem usar delay)
    if (now - lastMsg > 10000) {
        lastMsg = now;
        publish(detected);
    }
}

// Função para reconectar ao broker se a conexão cair
void reconnect() {
    while (!client.connected()) {
        Serial.print("Tentando conectar ao broker ");
        Serial.print(mqtt_server);
        Serial.print("...");

        if (client.connect(node_name)) {
            Serial.println("Conectado!");
        } else {
            Serial.print("falhou, rc=");
            Serial.print(client.state());
            Serial.println("tentando novamente em 5 segundos");
            delay(5000);
        }
    }
}

void publish(bool presence) {
    String msg;
    doc["presence"] = presence;
    serializeJson(doc, msg);

    Serial.print("Publicando mensagem: ");
    Serial.println(msg);
    client.publish(mqtt_topic_publish, msg.c_str()); // necessário transformar em string padrão
}