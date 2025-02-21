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

# --- Parameters for the Simulation ---
NUM_CLIENTS = 100         # Number of simulated clients
TOTAL_TRANSACTIONS = 1000 # Total number of transactions to be sent

# --- Global Metrics and Event Log ---
metrics = {
    'transactions_received': 0,
    'blocks_mined': 0,
    'requests_count': 0,
}
event_log = []  # List to store event entries

# --- Blockchain Implementation ---
class Blockchain:
    def __init__(self):
        self.chain = []  # List to store the blockchain
        self.pending_transactions = []  # List to store pending transactions
        self.create_genesis_block()  # Create the first block (genesis block)
        self.difficulty = 4  # Difficulty level for proof-of-work

    def create_genesis_block(self):
        # Create the first block in the blockchain (genesis block)
        genesis_block = {
            'index': 1,
            'timestamp': time.time(),
            'transactions': [],
            'proof': 1,
            'previous_hash': '0'
        }
        genesis_block['hash'] = self.hash_block(genesis_block)  # Compute hash for the genesis block
        self.chain.append(genesis_block)
        event_log.append("Genesis block created.")

    def get_last_block(self):
        return self.chain[-1]  # Get the last block in the chain

    def add_transaction(self, sender, recipient, amount):
        # Add a new transaction to the pending transactions list
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time()
        }
        self.pending_transactions.append(transaction)
        return len(self.chain) + 1  # Expected block index

    def mine_block(self):
        if not self.pending_transactions:
            return None  # No transactions to mine

        last_block = self.get_last_block()
        index = last_block['index'] + 1
        block = {
            'index': index,
            'timestamp': time.time(),
            'transactions': self.pending_transactions.copy(),
            'proof': 0,
            'previous_hash': last_block['hash']
        }

        # Perform Proof-of-Work to mine the block
        block = self.proof_of_work(block)
        block['hash'] = self.hash_block(block)  # Compute the block hash
        self.chain.append(block)  # Add mined block to the blockchain
        self.pending_transactions = []  # Clear the transaction pool
        return block

    def proof_of_work(self, block):
        # Proof-of-Work algorithm to find a valid proof for the block
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
        # Hash the block (excluding the hash field)
        block_copy = block.copy()
        block_copy.pop('hash', None)
        block_string = json.dumps(block_copy, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def get_chain(self):
        return self.chain  # Return the full blockchain

# --- Flask App and API Endpoints ---
app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')  # Unique node identifier
blockchain = Blockchain()

# Flask hook to count every incoming request
@app.before_request
def before_request_func():
    metrics['requests_count'] += 1

# HTML Template for the dashboard (with inline CSS and rotating Bitcoin logo)
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
        /* Rotating Bitcoin logo */
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
    <!-- Rotating Bitcoin Logo -->
    <img src="https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg" alt="Bitcoin Logo" class="rotating-logo">
    <h1>Blockchain Dashboard</h1>
    <div class="metrics">
        <h2>System Metrics</h2>
        <table>
            <tr><th>Description</th><th>Value</th></tr>
            <tr><td>Total number of blocks</td><td>{{ chain_length }}</td></tr>
            <tr><td>Pending transactions</td><td>{{ pending_transactions }}</td></tr>
            <tr><td>Transactions received</td><td>{{ transactions_received }}</td></tr>
            <tr><td>Blocks mined</td><td>{{ blocks_mined }}</td></tr>
            <tr><td>Total number of requests</td><td>{{ requests_count }}</td></tr>
        </table>
    </div>
    <div class="block-data">
        <h2>Last Block</h2>
        <pre>{{ last_block }}</pre>
    </div>
    <div class="log">
        <h2>Event Log</h2>
        {% for event in event_log %}
          <p>{{ event }}</p>
        {% endfor %}
    </div>
</body>
</html>
"""

# Dashboard route
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
                                  event_log=reversed(event_log))  # Show most recent events at the top

# New transaction endpoint
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()  # Get JSON data from the request
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):  # Check for missing data
        event_log.append("Error: Missing transaction data received.")
        return jsonify({'message': 'Missing transaction data'}), 400

    # Add the new transaction to the blockchain
    index = blockchain.add_transaction(values['sender'], values['recipient'], values['amount'])
    metrics['transactions_received'] += 1
    event_log.append(f"New transaction: {values['sender']} → {values['recipient']} ({values['amount']}).")
    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

# Mine block endpoint
@app.route('/mine', methods=['GET'])
def mine():
    block = blockchain.mine_block()
    if block:
        metrics['blocks_mined'] += 1
        event_log.append(f"Block {block['index']} mined with {len(block['transactions'])} transactions.")
        response = {
            'message': 'New block mined',
            'block': block
        }
        return jsonify(response), 200
    else:
        event_log.append("Mine request: No transactions to mine.")
        return jsonify({'message': 'No transactions to mine.'}), 400

# Get full chain endpoint
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.get_chain(),
        'length': len(blockchain.get_chain())
    }
    return jsonify(response), 200

# --- Simulation: Multiple clients sending transactions ---
def simulate_client(client_id, transactions_per_client, post_url):
    for i in range(transactions_per_client):
        transaction_data = {
            'sender': f'client_{client_id}',
            'recipient': f'client_{random.randint(1, NUM_CLIENTS)}',
            'amount': round(random.uniform(1, 100), 2)
        }
        try:
            requests.post(post_url, json=transaction_data, timeout=1)
            # Short pause to distribute load
            time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            event_log.append(f"Client {client_id} error with transaction {i}: {e}")

# Start the simulation
def start_simulation():
    event_log.append(f"Starting simulation with {NUM_CLIENTS} clients and {TOTAL_TRANSACTIONS} transactions.")
    transactions_per_client = TOTAL_TRANSACTIONS // NUM_CLIENTS
    threads = []
    post_url = "http://127.0.0.1:5000/transactions/new"
    for client_id in range(1, NUM_CLIENTS+1):
        t = threading.Thread(target=simulate_client, args=(client_id, transactions_per_client, post_url))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    event_log.append("Simulation completed.")

# --- Main Program ---
if __name__ == '__main__':
    # If "simulate" is passed as a command-line argument, start simulation mode
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        # Start the Flask server in a separate thread
        server_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, threaded=True))
        server_thread.daemon = True
        server_thread.start()
        # Wait a short time to allow the server to start
        time.sleep(2)
        start_simulation()
        # Server continues running
        server_thread.join()
    else:
        app.run(host='0.0.0.0', port=5000, threaded=True)  # Run the Flask server
