import pika
import serial
import json
import sqlite3
from serial.tools import list_ports
from datetime import datetime
import threading
import sys

QUEUE_NAME = 'entrada.eventos'
RABBITMQ_URL = "amqps://cyhjxgot:M3zU0_K0AOo2ag_F9u8rl4tJ1hKB0FYf@jaragua.lmq.cloudamqp.com/cyhjxgot"
DB_NAME = "rfid_tags.db"

modo_interativo = False
ser = None
conn = None
channel = None
serial_lock = threading.Lock()
db_lock = threading.Lock()
tag_event = threading.Event()
tag_lida_para_interacao = None
LISTEN_MSG = "[rasp2] Aguardando comunicação (C=cadastrar, E=editar, X=excluir, L=listar)"


def find_arduino_port():
    for p in list_ports.comports():
        if "Arduino" in p.description or "ttyACM" in p.device or "ttyUSB" in p.device:
            return p.device
    raise IOError("Arduino não encontrado")


def get_db_connection():
    # timeout aumenta o tempo de espera em caso de lock
    return sqlite3.connect(DB_NAME, timeout=10)


def init_db():
    with db_lock:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                tag TEXT UNIQUE,
                id_liberado INTEGER,
                dt_cadastro TEXT
            )
        """
        )
        conn.commit()
        conn.close()


def tag_autorizada(tag):
    with db_lock:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id_liberado FROM tags WHERE tag = ?", (tag,))
        row = cur.fetchone()
        conn.close()
        return row and row[0] == 1


def processa_mensagem(ch, method, properties, body):
    global modo_interativo, tag_lida_para_interacao
    try:
        dados = json.loads(body.decode())
        tipo = dados.get("tipo")
        tag = dados.get("tag", "").upper()
        if modo_interativo and tipo == "RFID":
            tag_lida_para_interacao = tag
            print(f"[rasp2] TAG capturada para interação: {tag}")
            tag_event.set()
            return
        if modo_interativo:
            return
        if tipo == "RFID":
            autorizado = tag_autorizada(tag)
            comando = "ACESSO_LIBERADO\n" if autorizado else "ACESSO_NEGADO\n"
            print(f"[rasp2] TAG: {tag} → {'Autorizado' if autorizado else 'Negado'}")
            with serial_lock:
                ser.write(comando.encode())
    except Exception as e:
        print("[rasp2] Erro ao processar mensagem:", e)


def aguardar_tag_da_fila():
    global tag_lida_para_interacao
    tag_event.clear()
    print("Aguardando TAG via RabbitMQ para interação...")
    tag_event.wait()
    tag = tag_lida_para_interacao
    tag_lida_para_interacao = None
    return tag


def listar_tags():
    with db_lock:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nome, tag, id_liberado, dt_cadastro FROM tags")
        rows = cur.fetchall()
        conn.close()
    if not rows:
        print("Nenhuma TAG cadastrada.")
    else:
        print("ID | Nome | TAG | Liberado | Data Cadastro")
        for id_, nome, tag, lib, dt in rows:
            status = 'Sim' if lib else 'Não'
            print(f"{id_} | {nome} | {tag} | {status} | {dt}")
    return rows


def cadastrar_tag():
    global modo_interativo
    modo_interativo = True
    print("\n[MODO CADASTRO]")
    nome = input("Nome do usuário: ").strip()
    tag = aguardar_tag_da_fila()
    print(f"TAG capturada: {tag}")
    while True:
        resp = input("Acesso liberado? (s/n): ").strip().lower()
        if resp in ('s', 'n'):
            liberado = (resp == 's')
            break
        print("Entrada inválida. Digite 's' ou 'n'.")
    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with db_lock:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO tags (nome, tag, id_liberado, dt_cadastro) VALUES (?, ?, ?, ?)",
                (nome, tag, int(liberado), dt)
            )
            conn.commit()
            conn.close()
        print("[rasp2] Cadastro salvo com sucesso.")
    except sqlite3.IntegrityError:
        print("[rasp2] Erro: TAG já cadastrada.")
    except sqlite3.OperationalError as e:
        if 'locked' in str(e).lower():
            print("[rasp2] Erro: banco de dados ocupado, tente novamente.")
        else:
            print(f"[rasp2] Erro de banco de dados: {e}")
    except Exception as e:
        print(f"[rasp2] Erro ao salvar: {e}")
    finally:
        modo_interativo = False
        print(LISTEN_MSG)


def editar_tag():
    rows = listar_tags()
    if not rows:
        print(LISTEN_MSG)
        return
    while True:
        try:
            id_ = int(input("Digite o ID da TAG a editar: ").strip())
            break
        except ValueError:
            print("ID inválido. Digite um número válido.")
    nome = input("Novo nome (ou Enter para manter): ").strip()
    while True:
        lib_in = input("Liberado? (s/n ou Enter para manter): ").strip().lower()
        if lib_in in ('s', 'n', ''):
            break
        print("Entrada inválida. Digite 's', 'n' ou pressione Enter.")
    fields, vals = [], []
    if nome:
        fields.append("nome = ?")
        vals.append(nome)
    if lib_in in ('s', 'n'):
        fields.append("id_liberado = ?")
        vals.append(1 if lib_in == 's' else 0)
    if not fields:
        print("Nada a atualizar.")
        print(LISTEN_MSG)
        return
    vals.append(id_)
    try:
        with db_lock:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE tags SET {', '.join(fields)} WHERE id = ?", vals)
            conn.commit()
            conn.close()
        print("[rasp2] TAG atualizada com sucesso.")
    except sqlite3.OperationalError as e:
        if 'locked' in str(e).lower():
            print("[rasp2] Erro: banco de dados ocupado, tente novamente.")
        else:
            print(f"[rasp2] Erro de banco de dados: {e}")
    except Exception as e:
        print(f"[rasp2] Erro ao atualizar: {e}")
    finally:
        print(LISTEN_MSG)


def excluir_tag():
    rows = listar_tags()
    if not rows:
        print(LISTEN_MSG)
        return
    while True:
        try:
            id_ = int(input("Digite o ID da TAG a excluir: ").strip())
            break
        except ValueError:
            print("ID inválido. Digite um número válido.")
    while True:
        confirm = input("Confirma exclusão? (s/n): ").strip().lower()
        if confirm in ('s', 'n'):
            break
        print("Entrada inválida. Digite 's' ou 'n'.")
    if confirm != 's':
        print("Exclusão cancelada.")
        print(LISTEN_MSG)
        return
    try:
        with db_lock:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM tags WHERE id = ?", (id_,))
            conn.commit()
            conn.close()
        print("[rasp2] TAG excluída com sucesso.")
    except sqlite3.OperationalError as e:
        if 'locked' in str(e).lower():
            print("[rasp2] Erro: banco de dados ocupado, tente novamente.")
        else:
            print(f"[rasp2] Erro de banco de dados: {e}")
    except Exception as e:
        print(f"[rasp2] Erro ao excluir: {e}")
    finally:
        print(LISTEN_MSG)


def monitorar_teclado():
    while True:
        try:
            cmd = input().strip().upper()
            if cmd == 'C':
                cadastrar_tag()
            elif cmd == 'E':
                editar_tag()
            elif cmd == 'X':
                excluir_tag()
            elif cmd == 'L':
                listar_tags()
                print(LISTEN_MSG)
        except KeyboardInterrupt:
            print("\n[rasp2] Interrompido no teclado. Encerrando monitor...")
            break


# Inicialização
init_db()
try:
    SERIAL_PORT = find_arduino_port()
    ser = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    print(f"[rasp2] Conectado ao Arduino na porta {SERIAL_PORT}")
except Exception as e:
    print("[rasp2] Erro ao conectar à serial:", e)
    sys.exit(1)

# Inicia monitor de teclado
threading.Thread(target=monitorar_teclado, daemon=True).start()

# Conecta RabbitMQ e inicia consumo
try:
    print("[rasp2] Conectando ao RabbitMQ...")
    params = pika.URLParameters(RABBITMQ_URL)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=processa_mensagem,
        auto_ack=True
    )
    print(LISTEN_MSG)
    channel.start_consuming()

except KeyboardInterrupt:
    print("\n[rasp2] Interrompido pelo usuário. Finalizando...")
    if channel:
        try: channel.close()
        except: pass
    if conn:
        try: conn.close()
        except: pass
    if ser:
        try: ser.close()
        except: pass
    print("[rasp2] Recursos liberados. Até mais!")
    sys.exit(0)

except Exception as e:
    print("[rasp2] Erro na conexão com RabbitMQ:", e)
