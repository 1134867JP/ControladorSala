import pika
import serial
import time
import json

SERIAL_PORT = '/dev/ttyACM0'
BAUD = 9600
QUEUE_NAME = 'entrada.eventos'

RABBITMQ_URL = "amqps://cyhjxgot:M3zU0_K0AOo2ag_F9u8rl4tJ1hKB0FYf@jaragua.lmq.cloudamqp.com/cyhjxgot"

def conecta_rabbitmq():
    print("[rasp1] Conectando ao RabbitMQ...")
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    print("[rasp1] Conectado ao RabbitMQ e fila declarada.")
    return conn, channel

try:
    # Conexão serial
    print(f"[rasp1] Conectando à serial {SERIAL_PORT} com baud {BAUD}...")
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    time.sleep(2)
    print("[rasp1] Serial conectada.")

    # Conexão com RabbitMQ
    conn, channel = conecta_rabbitmq()

    while True:
        try:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode('utf-8', errors='ignore').strip()
            print(f"[rasp1] [Serial] Leitura: {line}")

            if line.startswith("TAG:"):
                tag = line[4:].strip()
                msg = {
                    "tipo": "RFID",
                    "tag": tag
                }

                print(f"[rasp1] [RFID] TAG lida: {tag}")
                channel.basic_publish(
                    exchange='',
                    routing_key=QUEUE_NAME,
                    body=json.dumps(msg)
                )
                print(f"[rasp1] [RabbitMQ] Publicado na fila '{QUEUE_NAME}': {msg}")
            else:
                print("[rasp1] [Info] Dados ignorados (não é uma TAG RFID).")

        except Exception as e:
            print("[rasp1] Erro no loop principal:", e)
            time.sleep(1)

except KeyboardInterrupt:
    print("\n[rasp1] Interrupção por teclado (Ctrl+C) detectada. Encerrando...")

finally:
    try:
        if ser and ser.is_open:
            ser.close()
            print("[rasp1] Conexão serial fechada.")
    except:
        pass
    try:
        if conn and conn.is_open:
            conn.close()
            print("[rasp1] Conexão com RabbitMQ fechada.")
    except:
        pass
