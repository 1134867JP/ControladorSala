# ControladorSala

Sistema de controle de acesso para salas utilizando RFID, Arduinos, Raspberry Pi e RabbitMQ.

## Descrição

Este projeto implementa um controlador de acesso que envolve dois Arduinos e duas Raspberry Pi.  
- O *producer* (Raspberry Pi 1 + Arduino 1) detecta a aproximação de uma tag RFID e envia um evento via RabbitMQ.  
- O *consumer* (Raspberry Pi 2 + Arduino 2) recebe o evento, verifica se a TAG está cadastrada (em SQLite ou arquivo `.txt`) e aciona LEDs e buzzer conforme o resultado.  
- Modo de cadastro (‘C’): permite inserir, editar e excluir TAGs autorizadas pelo terminal.

## Funcionalidades

- Leitura de TAGs RFID  
- Comunicação via RabbitMQ  
- Cadastro, edição e remoção de TAGs (nome, UID, permissão e data de cadastro)  
- Indicação visual (LED verde/vermelho) e sonora (buzzer)  
- Arquivo de banco de dados em SQLite ou TXT  

## Requisitos

- Raspberry Pi (com Python 3)  
- Arduino (IDE e bibliotecas RFID)  
- Node de mensageria RabbitMQ  
- SQLite (opcional) ou permissão de escrita em arquivo `.txt`  
- Bibliotecas Python: `pika`, `sqlite3` (se SQLite for usado)

## Instalação

1. **Configure o RabbitMQ**  
   - Instale e inicie o servidor RabbitMQ.  
   - Crie um usuário ou use o padrão (`guest/guest`).

2. **Producer (Raspberry Pi 1 + Arduino 1)**  
   - Faça upload de `producer.ino` no Arduino 1.  
   - No Rasp Pi 1, ajuste `producer.py` com as credenciais do RabbitMQ e execute:
     python3 producer.py

3. **Consumer (Raspberry Pi 2 + Arduino 2)**  
   - Faça upload de `consumer.ino` no Arduino 2.  
   - No Rasp Pi 2, ajuste `consumer.py` com o caminho do banco de dados e credenciais do RabbitMQ e execute:
     python3 consumer.py

## Uso

- Ao aproximar uma TAG do leitor do *producer*, o evento é enviado e o *consumer* decide:
  - **LED verde + bip curto**: acesso autorizado  
  - **LED vermelho + bip longo**: acesso negado  
- Pressione `C` no console do *consumer* para entrar no modo de cadastro:
  - Siga as instruções para adicionar, editar ou remover TAGs.

## Contribuidores

### Rasp1
- Ricardo Groth da Silva  (1134872)
- Ricardo Basso Gunther  (1134953)

### Rasp2
- Nycolas Musskopf Fachi  (1134317)
- João Pedro Rodrigues (1134867)  
