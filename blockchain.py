#!/usr/bin/env python3
import hashlib
import json
import time
import threading
import random
import sys
from uuid import uuid4
from flask import Flask, jsonify, request, render_template_string
import requests

# --- Parameter für Simulation ---
NUM_CLIENTS = 100         # Anzahl der simulierten Clients
TOTAL_TRANSACTIONS = 1000 # Gesamte Anzahl von Transaktionen, die gesendet werden sollen

# --- Globale Metriken und Ereignisprotokoll ---
metrics = {
    'transactions_received': 0,
    'blocks_mined': 0,
    'requests_count': 0,
}
event_log = []  # Liste mit Ereigniseinträgen

# --- Blockchain-Implementierung ---
class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
        self.difficulty = 4  # Schwierigkeitsgrad für den Proof-of-Work

    def create_genesis_block(self):
        genesis_block = {
            'index': 1,
            'timestamp': time.time(),
            'transactions': [],
            'proof': 1,
            'previous_hash': '0'
        }
        genesis_block['hash'] = self.hash_block(genesis_block)
        self.chain.append(genesis_block)
        event_log.append("Genesis-Block erstellt.")

    def get_last_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, recipient, amount):
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time()
        }
        self.pending_transactions.append(transaction)
        return len(self.chain) + 1  # Voraussichtlicher Blockindex

    def mine_block(self):
        if not self.pending_transactions:
            return None  # Keine Transaktionen zum Schürfen

        last_block = self.get_last_block()
        index = last_block['index'] + 1
        block = {
            'index': index,
            'timestamp': time.time(),
            'transactions': self.pending_transactions.copy(),
            'proof': 0,
            'previous_hash': last_block['hash']
        }

        # Proof-of-Work durchführen
        block = self.proof_of_work(block)
        block['hash'] = self.hash_block(block)
        self.chain.append(block)
        self.pending_transactions = []  # Mempool leeren
        return block

    def proof_of_work(self, block):
        proof = 0
        block['proof'] = proof
        computed_hash = self.hash_block(block)
        while not computed_hash.startswith('0' * self.difficulty):
            proof += 1
            block['proof'] = proof
            computed_hash = self.hash_block(block)
        return block

    @staticmethod
    def hash_block(block):
        # Kopie erstellen, um das eventuelle "hash"-Feld auszuschließen
        block_copy = block.copy()
        block_copy.pop('hash', None)
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def get_chain(self):
        return self.chain

# --- Flask-App und API-Endpoints ---
app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

# Flask-Hook, um jeden Request mitzuzählen
@app.before_request
def before_request_func():
    metrics['requests_count'] += 1

# HTML-Vorlage für das Dashboard (mit inline CSS und rotiertem Bitcoin-Logo)
UI_TEMPLATE = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Blockchain Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; position: relative; }
        h1, h2 { color: #333; }
        .metrics, .log, .block-data { margin-top: 20px; background: #fff; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metrics table { border-collapse: collapse; width: 100%; }
        .metrics th, .metrics td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .metrics th { background-color: #f2f2f2; }
        .log { height: 200px; overflow-y: scroll; }
        pre { background: #eee; padding: 10px; border-radius: 5px; }
        /* Rotierendes Bitcoin-Logo */
        @keyframes rotation {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .rotating-logo {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 50px;
            height: 50px;
            animation: rotation 5s infinite linear;
        }
    </style>
</head>
<body>
    <!-- Rotierendes Bitcoin-Logo -->
    <img src="https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg" alt="Bitcoin Logo" class="rotating-logo">
    <h1>Blockchain Dashboard</h1>
    <div class="metrics">
        <h2>Systemmetriken</h2>
        <table>
            <tr><th>Beschreibung</th><th>Wert</th></tr>
            <tr><td>Gesamtanzahl Blöcke</td><td>{{ chain_length }}</td></tr>
            <tr><td>Ausstehende Transaktionen</td><td>{{ pending_transactions }}</td></tr>
            <tr><td>Erhaltene Transaktionen</td><td>{{ transactions_received }}</td></tr>
            <tr><td>Geminete Blöcke</td><td>{{ blocks_mined }}</td></tr>
            <tr><td>Gesamtzahl der Requests</td><td>{{ requests_count }}</td></tr>
        </table>
    </div>
    <div class="block-data">
        <h2>Letzter Block</h2>
        <pre>{{ last_block }}</pre>
    </div>
    <div class="log">
        <h2>Ereignisprotokoll</h2>
        {% for event in event_log %}
          <p>{{ event }}</p>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    chain_length = len(blockchain.get_chain())
    pending = len(blockchain.pending_transactions)
    last_block = blockchain.get_last_block()
    last_block_str = json.dumps(last_block, indent=4, sort_keys=True)
    return render_template_string(UI_TEMPLATE,
                                  chain_length=chain_length,
                                  pending_transactions=pending,
                                  transactions_received=metrics['transactions_received'],
                                  blocks_mined=metrics['blocks_mined'],
                                  requests_count=metrics['requests_count'],
                                  last_block=last_block_str,
                                  event_log=reversed(event_log))  # Neueste Ereignisse oben

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        event_log.append("Fehler: Fehlende Transaktionsdaten empfangen.")
        return jsonify({'message': 'Fehlende Transaktionsdaten'}), 400

    index = blockchain.add_transaction(values['sender'], values['recipient'], values['amount'])
    metrics['transactions_received'] += 1
    event_log.append(f"Neue Transaktion: {values['sender']} → {values['recipient']} ({values['amount']}).")
    response = {'message': f'Transaktion wird in Block {index} aufgenommen.'}
    return jsonify(response), 201

@app.route('/mine', methods=['GET'])
def mine():
    block = blockchain.mine_block()
    if block:
        metrics['blocks_mined'] += 1
        event_log.append(f"Block {block['index']} geschürft mit {len(block['transactions'])} Transaktionen.")
        response = {
            'message': 'Neuer Block geschürft',
            'block': block
        }
        return jsonify(response), 200
    else:
        event_log.append("Mine-Aufruf: Keine Transaktionen vorhanden.")
        return jsonify({'message': 'Keine Transaktionen zum Schürfen vorhanden.'}), 400

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.get_chain(),
        'length': len(blockchain.get_chain())
    }
    return jsonify(response), 200

# --- Simulation: Mehrere Clients senden Transaktionen ---
def simulate_client(client_id, transactions_per_client, post_url):
    for i in range(transactions_per_client):
        transaction_data = {
            'sender': f'client_{client_id}',
            'recipient': f'client_{random.randint(1, NUM_CLIENTS)}',
            'amount': round(random.uniform(1, 100), 2)
        }
        try:
            requests.post(post_url, json=transaction_data, timeout=1)
            # Kurze Pause, um die Last zu verteilen
            time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            event_log.append(f"Client {client_id} Fehler bei Transaktion {i}: {e}")

def start_simulation():
    event_log.append(f"Starte Simulation mit {NUM_CLIENTS} Clients und insgesamt {TOTAL_TRANSACTIONS} Transaktionen.")
    transactions_per_client = TOTAL_TRANSACTIONS // NUM_CLIENTS
    threads = []
    post_url = "http://127.0.0.1:5000/transactions/new"
    for client_id in range(1, NUM_CLIENTS+1):
        t = threading.Thread(target=simulate_client, args=(client_id, transactions_per_client, post_url))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    event_log.append("Simulation abgeschlossen.")

# --- Hauptprogramm ---
if __name__ == '__main__':
    # Falls über Kommandozeilenparameter "simulate" angegeben wird, starte den Simulationsmodus.
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        # Starte den Flask-Server in einem separaten Thread
        server_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, threaded=True))
        server_thread.daemon = True
        server_thread.start()
        # Kurze Wartezeit, damit der Server startet
        time.sleep(2)
        start_simulation()
        # Der Server läuft weiter
        server_thread.join()
    else:
        app.run(host='0.0.0.0', port=5000, threaded=True)
