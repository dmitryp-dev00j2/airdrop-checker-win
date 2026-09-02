import argparse
import csv
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from airdrop_checker.protocols import check_address, SUPPORTED_PROTOCOLS

write_lock = threading.Lock()

def process_address(address: str, protocols: list[str], retries: int = 3) -> dict:
    # TODO: find a cleaner way to filter out invalid hex strings before sending requests
    address = address.strip()
    if not address:
        return {}
    
    attempt = 0
    backoff = 1.5
    while attempt < retries:
        try:
            results = check_address(address, protocols)
            # print(f"DEBUG: raw check output for {address}: {results}")
            return {"address": address, "status": "success", "results": results}
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                return {"address": address, "status": "failed", "error": str(e), "results": {}}
            # Linear backoff on hit rate limit or network jitter
            time.sleep(backoff * attempt)

def main():
    parser = argparse.ArgumentParser(
        description="Batch check EVM/Starknet addresses for multiple airdrop claim lists.",
        epilog="Example: checker.py -i addrs.txt -o out.csv -p optimism,starknet"
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input text file containing one address per line.")
    parser.add_argument("-o", "--output", required=True, help="Path to output CSV results file.")
    parser.add_argument("-c", "--concurrency", type=int, default=4, help="Number of concurrent worker threads.")
    parser.add_argument("-p", "--protocols", help="Comma-separated list of protocols to check. Defaults to all supported.")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    selected_protocols = SUPPORTED_PROTOCOLS
    if args.protocols:
        selected_protocols = [p.strip() for p in args.protocols.split(",") if p.strip()]
        invalid = [p for p in selected_protocols if p not in SUPPORTED_PROTOCOLS]
        if invalid:
            print(f"Error: Unknown protocols: {', '.join(invalid)}", file=sys.stderr)
            print(f"Supported protocols: {', '.join(SUPPORTED_PROTOCOLS)}", file=sys.stderr)
            sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            addresses = [line.strip() for line in f if line.strip()]
    except IOError as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not addresses:
        print("Error: Input file is empty.", file=sys.stderr)
        sys.exit(1)

    headers = ["address", "status"]
    for proto in selected_protocols:
        headers.extend([f"{proto}_eligible", f"{proto}_amount"])
    headers.append("errors")

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    except IOError as e:
        print(f"Error initializing output CSV file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting check of {len(addresses)} addresses across {len(selected_protocols)} protocols...")
    print(f"Concurrency: {args.concurrency} | Output: {output_path}")

    completed = 0
    total = len(addresses)

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(process_address, addr, selected_protocols): addr
            for addr in addresses
        }
        
        for future in as_completed(futures):
            res = future.result()
            if not res:
                continue
                
            addr = res["address"]
            status = res["status"]
            results_data = res.get("results", {})
            err_msg = res.get("error", "")
            
            row = [addr, status]
            for proto in selected_protocols:
                proto_res = results_data.get(proto, {})
                eligible = proto_res.get("eligible", False)
                amount = proto_res.get("amount", 0)
                row.extend([eligible, amount])
            row.append(err_msg)

            with write_lock:
                try:
                    with open(output_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)
                except IOError as e:
                    print(f"\nWarning: Failed to write row for {addr}: {e}", file=sys.stderr)

            completed += 1
            sys.stdout.write(f"\rProgress: {completed}/{total} processed...")
            sys.stdout.flush()

    print("\nAll done! Results saved to output CSV.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(130)
