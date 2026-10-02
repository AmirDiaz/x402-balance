#!/usr/bin/env python3
"""x402-balance — zero-dependency USDC payment watcher for EVM chains.

Purpose: watch any address for incoming USDC (the settlement asset of the
x402 "HTTP 402 Payment Required" agent-payment pattern on Base). Prints the
balance, optionally polls until money arrives, exits with machine-friendly
status codes so CI / agents / cron jobs can react to "did I get paid?".

No API keys, no web3.py, no eth_account — just a JSON-RPC eth_call.

Usage:
  x402-balance <address>                     # one-shot balance (Base mainnet)
  x402-balance <address> --watch              # poll until balance > 0
  x402-balance <address> --network sepolia    # Base Sepolia testnet
  x402-balance <address> --json               # machine-readable output
  x402-balance <address> --token <contract>   # any ERC-20

Exit codes:
  0  balance is non-zero (or --json one-shot succeeded)
  3  balance is zero
  1  usage / network / RPC error
"""
import argparse
import json
import sys
import time
import urllib.request

NETWORKS = {
    "base": {
        "rpc": "https://mainnet.base.org",
        "label": "Base mainnet",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    },
    "sepolia": {
        "rpc": "https://sepolia.base.org",
        "label": "Base Sepolia",
        "usdc": "0x036CbD53842c5426634e7929541EC2318f3dCF7e",
    },
    "ethereum": {
        "rpc": "https://eth.drpc.org",
        "label": "Ethereum mainnet",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    },
}

SELECTOR_BALANCEOF = "0x70a08231"  # keccak256("balanceOf(address)")[:4]


def is_address(s):
    return len(s) == 42 and s.startswith("0x") and all(
        c in "0123456789abcdefABCDEF" for c in s[2:]
    )


def rpc_call(rpc, to, data):
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    }).encode()
    # some public RPCs 403 on python-urllib UA
    req = urllib.request.Request(rpc, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(f"RPC error: {d['error']}")
    return d.get("result", "0x0")


def balance_of(rpc, token, address, decimals):
    data = SELECTOR_BALANCEOF + "0" * 24 + address[2:].lower()
    raw = rpc_call(rpc, token, data)
    return int(raw, 16) / (10 ** decimals)


def main():
    ap = argparse.ArgumentParser(
        prog="x402-balance",
        description="Check / watch USDC (or any ERC-20) balance for an EVM "
                    "address — built for x402-style agent payouts on Base.",
    )
    ap.add_argument("address", help="0x-prefixed EVM address")
    ap.add_argument("--network", "-n", default="base", choices=sorted(NETWORKS),
                    help="preset network (default: base)")
    ap.add_argument("--rpc", help="override RPC endpoint")
    ap.add_argument("--token", help="override token contract address")
    ap.add_argument("--decimals", type=int, default=6,
                    help="token decimals (default 6 = USDC)")
    ap.add_argument("--watch", action="store_true",
                    help="poll until balance is non-zero, then exit 0")
    ap.add_argument("--interval", type=float, default=15.0,
                    help="--watch poll interval seconds (default 15)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="emit a single JSON object")
    ap.add_argument("--max-polls", type=int, default=0,
                    help="--watch give up after N polls (0 = forever)")
    args = ap.parse_args()

    if not is_address(args.address):
        print("error: address must be a 0x… 42-char hex string", file=sys.stderr)
        return 1
    net = NETWORKS[args.network]
    rpc = args.rpc or net["rpc"]
    token = args.token or net["usdc"]
    if args.token and not is_address(args.token):
        print("error: --token must be a contract address", file=sys.stderr)
        return 1

    polls = 0
    while True:
        try:
            bal = balance_of(rpc, token, args.address, args.decimals)
        except Exception as e:
            if args.as_json:
                print(json.dumps({"error": str(e), "network": args.network}))
            else:
                print(f"error: {e}", file=sys.stderr)
            return 1

        if args.as_json:
            print(json.dumps({
                "address": args.address,
                "network": args.network,
                "rpc": rpc,
                "token": token,
                "decimals": args.decimals,
                "balance": f"{bal:.{args.decimals}f}",
                "balance_raw": f"{bal * (10 ** args.decimals):.0f}",
                "paid": bal > 0,
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }))
        else:
            stamp = time.strftime("%H:%M:%S")
            state = "PAID" if bal > 0 else "waiting"
            print(f"[{stamp}] {net['label']} USDC {bal:.6f} @ {args.address} ({state})")

        if not args.watch:
            return 0 if bal > 0 else 3
        if bal > 0:
            return 0
        polls += 1
        if args.max_polls and polls >= args.max_polls:
            if args.as_json:
                print(json.dumps({"gave_up": True, "polls": polls}))
            else:
                print(f"gave up after {polls} polls; balance still zero")
            return 3
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
