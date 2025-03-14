# blockchain-distributed-system

View the detailed documentation here:
https://www.overleaf.com/read/wkpkccfstshp#ece09a

A Python-based blockchain with transaction simulation and monitoring.

## Features
- **Core**: SHA-256 hashing, Proof-of-Work, Genesis block, transaction mempool  
- **API**: REST endpoints for transactions/mining/chain inspection  
- **Simulation**: 100+ clients, 1000+ transactions, threaded load testing  
- **Dashboard**: Real-time metrics, event log, block explorer  

## Requirements
pip install flask requests

## Quick Start
### Run node:
python blockchain.py

## Access dashboard:
http://localhost:5000

## Key Commands
Action                Command
--------------------- --------------------------
Create transaction    POST /transactions/new
Mine block           GET /mine
Get chain           GET /chain
Start simulation     python blockchain.py simulate

## Configuration in code
NUM_CLIENTS = 100          # Simulated users
TOTAL_TRANSACTIONS = 1000  # Total test transactions
difficulty = 4             # PoW complexity

## Structure
Blockchain:  Chain validation, mining logic
Flask App:   API endpoints + web UI
Simulation:  Client stress-test module
Dashboard:   Metrics visualization

## Metrics tracked
Total blocks
Pending transactions
System requests
Mining events

