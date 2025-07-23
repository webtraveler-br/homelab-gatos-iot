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

const char* mqtt_server = "192.168.1.67";
const char* mqtt_topic_publish = "sensores/nodes/table_presence";
const int mqtt_port = 1883;

int detected = 0;
long lastMsg = 0;

void reconnect();
void publish(int);

void setup() {
	Serial.begin(115200);

	pinMode(pin_heat_sensor, INPUT);

	// Descomente a linha abaixo para forçar a aparição do portal de configuração.
	// wm.resetSettings();

	// Se o usuário não configurar em 10 minutos, o ESP reinicia.
	wm.setConfigPortalTimeout(600);

	if (!wm.autoConnect(node_name)) {
		Serial.println("Tempo limite atingido. Reiniciando...");
		ESP.restart();
	}
	else {
		Serial.println("Conectado!");
		Serial.print("Endereço IP: ");
		Serial.println(WiFi.localIP());
	}

	client.setServer(mqtt_server, mqtt_port);
}

void loop() {
	int sensor_value = digitalRead(pin_heat_sensor);
	long now = millis();

	if (sensor_value == HIGH && detected == LOW) {
		Serial.println("Detectado!");
	}
	else if (sensor_value == LOW && detected == HIGH) {
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
		Serial.print("Tentando conectar ao broker...");

		if (client.connect(node_name)) {
			Serial.println("Conectado!");
		}
		else {
			Serial.print("falhou, rc=");
			Serial.print(client.state());
			Serial.println("tentando novamente em 5 segundos");
			delay(5000);
		}
	}
}

void publish(int presence) {
	String msg;

	doc["presence"] = presence;
	serializeJson(doc, msg);

	Serial.print("Publicando mensagem: ");
	Serial.println(msg);
	client.publish(mqtt_topic_publish, msg.c_str()); // necessário transformar em string padrão
}