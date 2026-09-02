import httpx
import logging

logger = logging.getLogger("airdrop_checker")

def clean_starknet_addr(addr: str) -> str:
    # Starknet provisions API requires a strict 64-character hex length (excluding 0x).
    # Without zero-padding, the API returns a 400 or 404 even if the address has an allocation.
    val = addr.lower().strip()
    if val.startswith("0x"):
        val = val[2:]
    return "0x" + val.zfill(64)

async def check_starknet(client: httpx.AsyncClient, address: str) -> float:
    cleaned = clean_starknet_addr(address)
    url = f"https://provisionsapi.starknet.io/provisions/{cleaned}"
    resp = await client.get(url, timeout=10.0)
    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    
    data = resp.json()
    return float(data.get("allocation", 0.0))

async def check_zksync(client: httpx.AsyncClient, address: str) -> float:
    url = f"https://api.zksync.io/api/v1/airdrop/{address.lower()}"
    resp = await client.get(url, timeout=10.0)
    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    
    data = resp.json()
    if data.get("eligible") and "amount" in data:
        return float(data["amount"]) / 10**18
    return 0.0

async def check_layerzero(client: httpx.AsyncClient, address: str) -> float:
    url = f"https://api.layerzero.foundation/claim/{address.lower()}"
    resp = await client.get(url, timeout=10.0)
    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    
    data = resp.json()
    return float(data.get("allocation", {}).get("total", 0.0))

async def check_eigenlayer(client: httpx.AsyncClient, address: str) -> float:
    # Eigenlayer claims API structure changed across season 1 and 2.
    # We need to parse recursively or check multiple keys in the returned payload.
    url = f"https://claims.eigenfoundation.org/api/proof/{address.lower()}"
    resp = await client.get(url, timeout=10.0)
    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    
    data = resp.json()
    # print(f"eigen response for {address}: {data}")
    
    total = 0.0
    claims = data.get("claims", [])
    if not isinstance(claims, list):
        claims = [data] if "amount" in data else []
        
    for claim in claims:
        raw_val = claim.get("amount") or claim.get("value")
        if raw_val:
            try:
                total += float(raw_val) / 1e18
            except ValueError:
                pass
    return total
