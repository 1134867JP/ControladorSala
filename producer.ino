#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10   // SDA do RC522
#define RST_PIN 9   // RST do RC522

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID pronto. Aproxime uma tag...");
}

void loop() {
  // Verifica se há nova tag presente
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Monta o UID em string
  String tagID = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) tagID += "0";
    tagID += String(rfid.uid.uidByte[i], HEX);
  }

  tagID.toUpperCase();  // deixa em maiúsculo por consistência

  Serial.print("TAG:");
  Serial.println(tagID);  // envia no formato TAG:XXXXXXXX

  // Aguarda um tempo antes de permitir nova leitura
  delay(1000);
  rfid.PICC_HaltA();          // Para a leitura da tag
  rfid.PCD_StopCrypto1();     // Encerra comunicação segura
}