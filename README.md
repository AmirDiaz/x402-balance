# x402-balance

Zero-dependency CLI that answers one question for agents and humans on Base: **"did the payment land?"**

Watches any EVM address for incoming USDC — the settlement asset used by x402-style
"HTTP 402 Payment Required" agent payouts on Base — via a plain `eth_call` to a public
RPC. No web3.py, no eth_account, no API keys, no compilation step.

```bash
$ python3 x402_balance.py 0x3906E8C9551F26581D23411c9Db817ec9a724D5C
[19:44:55] Base mainnet USDC 0.000000 @ 0x3906...4D5C (waiting)   # exit 3

$ python3 x402_balance.py 0x28C6c06298d514Db089934071355E5743bf21d60 --network ethereum
[19:45:25] Ethereum mainnet USDC 51951.298220 @ 0x28C6...d60 (PAID)  # exit 0
```

## Why

Agents that get paid over HTTP 402 negotiation settle into a wallet that is usually
checked by hand in a block explorer. This tool makes "has my payout arrived?" a
scriptable, zero-setup check:

- cron / CI friendly exit codes: `0` = paid, `3` = still zero, `1` = RPC/usage error
- `--watch` parks until the balance goes non-zero, then exits `0`
- `--json` emits one parseable object for pipelines and MCP-style tool wrappers

Verified against live chain state on 2026-10-02: reads
`51951.298220 USDC` for `0x28C6c06298d514Db089934071355E5743bf21d60` (Ethereum mainnet,
block `0x18e5bbb`) and `0.000000 USDC` for the author's Base address at Base mainnet
block `0x31ad686` (2026-10-02 19:44 UTC).

## Usage

```
x402_balance.py <address> [--network base|sepolia|ethereum] [--rpc URL]
                [--token CONTRACT] [--decimals N] [--watch]
                [--interval SEC] [--max-polls N] [--json]
```

| Flag | Meaning |
|------|---------|
| `--network` | `base` (default), `sepolia` (Base Sepolia), `ethereum` |
| `--rpc` | override the public RPC endpoint |
| `--token` | any ERC-20 contract address (default: native USDC of the network) |
| `--decimals` | token decimals (default 6, USDC) |
| `--watch` | poll `--interval` seconds until balance > 0, then exit `0` |
| `--max-polls` | give up after N polls (default: forever) |
| `--json` | one JSON object instead of human lines |

Token contracts baked in:

| Network | USDC |
|---------|------|
| Base mainnet | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Base Sepolia | `0x036CbD53842c5426634e7929541EC2318f3dCF7e` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |

### Patterns

Cron job that tweets when paid:

```bash
*/5 * * * * python3 x402_balance.py $WALLET --json | jq -r 'select(.paid) | .balance'
```

Agent tool wrapper — one call, one answer:

```json
{"paid": false, "balance": "0.000000", "network": "base", "token": "0x8335...2913"}
```

Wait synchronously for a settle:

```bash
python3 x402_balance.py $WALLET --watch --interval 30
```

## Implementation notes

- `balanceOf(address)` is `0x70a08231` + the 32-byte left-padded address; the response
  is a hex uint256 scaled by `10**decimals`.
- Public RPCs frequently return `403` to `python-urllib` user agents, so the client
  sends `User-Agent: curl/8.0`. That is the only "trick" in the file.
- Everything is stdlib `urllib.request`; the whole tool is one ~180-line file with no
  install step, mirroring the dependency-free style of
[sourcey-tracker](https://github.com/AmirDiaz/sourcey-tracker).

## License

MIT — see `LICENSE`.
