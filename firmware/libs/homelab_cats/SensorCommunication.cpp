#include "SensorCommunication.h"

SensorCommunication::SensorCommunication(const char* node_name) : _client(_esp_client) { // client precisa estar na lista de inicialização
    _node_name = node_name;
    strcpy(_mqtt_server_ip, "");
    _topic_publish = nullptr;
    _topic_subscribe = nullptr;
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

void SensorCommunication::setup_mqtt(const char* topic_publish, int port, const char* topic_subscribe, void (*callback)(const char*, const JsonDocument&)) {
    Serial.println("Configurando MQTT...");

    _topic_publish = topic_publish;
    _mqtt_port = port;
    _topic_subscribe = topic_subscribe;
    _user_callback = callback;
    _client.setServer(_mqtt_server_ip, port);

    if (_topic_subscribe) {
        _client.setCallback([this](char* topic, byte* payload, unsigned int length) {
            this->callback_json_wrapper(topic, payload, length);
        });
    }

    Serial.println("MQTT configurado.");
}

void SensorCommunication::callback_json_wrapper(const char* topic, const byte* payload, unsigned int length) {
    JsonDocument cmd_doc;
    String json_str((const char*)payload, length);
    DeserializationError error = deserializeJson(cmd_doc, json_str);
    if (error) {
        Serial.print("Erro ao parsear JSON: ");
        Serial.println(error.c_str());
        return;
    }
    if (_user_callback) {
        _user_callback(topic, cmd_doc);
    }
    else {
        Serial.print("Nenhum callback definido para mensagens MQTT");
    }
}

void SensorCommunication::reconnect() {
    while (!_client.connected()) {
        Serial.println("Tentando conectar ao broker MQTT...");

        if (_client.connect(_node_name)) {
            Serial.println("Conectado!");
            if (_topic_subscribe) {
                _client.subscribe(_topic_subscribe);
                Serial.print("Inscrito no tópico: ");
                Serial.println(_topic_subscribe);
            }
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