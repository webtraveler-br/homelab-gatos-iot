#include "SensorCommunication.h"

SensorCommunication::SensorCommunication(const char* node_name) : _client(_esp_client) { // client precisa estar na lista de inicialização
    _node_name = node_name;
    strcpy(_mqtt_server_ip, "");
}

void SensorCommunication::setup_wifi(bool reset_settings) {
    Serial.println("Configurando WiFi...");

    if (reset_settings) {
        _wm.resetSettings();
    }

    // Adiciona um campo novo ao wifi manager, permitindo configurar o IP do MQTT
    WiFiManagerParameter mqtt_server_ip("server", "MQTT Server IP", _mqtt_server_ip, 40);
    _wm.addParameter(&mqtt_server_ip);

    // Se o usuário não configurar em 10 minutos, o ESP reinicia.
    _wm.setConfigPortalTimeout(600);

    if (!_wm.autoConnect(_node_name)) {
        Serial.println("Tempo limite atingido. Reiniciando...");
        ESP.restart();
    }
    else {
        Serial.println("Conectado!");
        Serial.print("Endereço IP do ESP: ");
        Serial.println(WiFi.localIP());
    }

    strcpy(_mqtt_server_ip, mqtt_server_ip.getValue());
    Serial.print("Endereço IP do MQTT: ");
    Serial.println(_mqtt_server_ip);
}

void SensorCommunication::setup_mqtt(const char* topic_publish, int port) {
    Serial.println("Configurando MQTT...");

    _topic_publish = topic_publish;
    _mqtt_port = port;
    _client.setServer(_mqtt_server_ip, port);

    Serial.println("MQTT configurado.");
}

void SensorCommunication::reconnect() {
    while (!_client.connected()) {
        Serial.println("Tentando conectar ao broker MQTT...");

        if (_client.connect(_node_name)) {
            Serial.println("Conectado!");
        }
        else {
            Serial.print("Falhou, rc=");
            Serial.print(_client.state());
            Serial.println("Tentando novamente em 5 segundos...");
            delay(5000);
        }
    }
}

void SensorCommunication::loop() {
    if (!_client.connected()) {
        reconnect();
    }
    _client.loop();
}

bool SensorCommunication::publish(JsonDocument& doc) {
    String msg;
    serializeJson(doc, msg);

    Serial.print("Publicando mensagem: ");
    Serial.println(msg);
    return _client.publish(_topic_publish, msg.c_str()); // necessário transformar em string padrão
}