#define LED_VERDE     7
#define LED_VERMELHO  8
#define BUZZER_PIN    9

unsigned long tempoUltimaAcao = 0;
bool acessoLiberado = false;

void setup() {
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  Serial.begin(9600);

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, HIGH);  // vermelho ligado por padrão
  digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg == "ACESSO_LIBERADO") {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(500);
      digitalWrite(BUZZER_PIN, LOW);

      digitalWrite(LED_VERMELHO, LOW);
      digitalWrite(LED_VERDE, HIGH);
      acessoLiberado = true;
      tempoUltimaAcao = millis();
    }
    else if (msg == "ACESSO_NEGADO") {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      delay(100);
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  // Se passou 3s após liberação, volta o LED vermelho
  if (acessoLiberado && millis() - tempoUltimaAcao >= 3000) {
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_VERMELHO, HIGH);
    acessoLiberado = false;
  }
}
