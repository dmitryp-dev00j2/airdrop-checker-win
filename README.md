# airdrop-checker-win

A command-line tool I wrote to quickly check a list of EVM and Starknet addresses against multiple airdrop allocations. It runs concurrent queries to save time when checking dozens of wallets, and writes results incrementally to a CSV so progress isn't lost if an endpoint rate-limits us.

Supported networks/airdrops:
* LayerZero (official allocation API)
* Starknet (Provisions distribution endpoint)
* Scroll (Sessions / Marks eligibility)

## Installation

Clone this repository and install the dependencies:

```cmd
pip install -r requirements.txt
```

## Usage

Prepare a text file containing one address per line. It can handle both EVM addresses (`0x...`) and Starknet addresses (`0x...` with 64+ hex chars).

To run the check:

```cmd
python checker.py --addresses wallets.txt --output results.csv
```

Options:
* `--addresses`: Path to the text file with addresses (required).
* `--output`: Output CSV file path (defaults to `results.csv`).
* `--concurrency`: Number of concurrent workers (default is 3 to avoid aggressive rate-limiting).
* `--skip-starknet`: Skip querying Starknet endpoints if you only care about EVM.

<!-- verified: 2026-09-14 -->
