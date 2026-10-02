# x402-balance — verification report

Date: 2026-10-02 · Author: AmirDiaz · Tool: `x402_balance.py` v1.0.0

## Claim

A single-file, stdlib-only Python CLI can watch for incoming USDC on Base
(and any EVM network with a public JSON-RPC) with no API keys, no web3.py,
no eth_account, and machine-friendly exit codes.

## Method

The tool issues `eth_call` with `balanceOf(address)` (`0x70a08231` selector)
against the network's USDC contract, decodes the returned uint256, and scales
it by `10^decimals`. Watching is a poll loop; JSON mode serializes one object.

## Results (all executed live, 2026-10-02 UTC)

| # | Command | Expected | Observed | Pass |
|---|---------|----------|----------|------|
| 1 | `x402_balance.py 0x3906…4D5C` | prints balance, exit 3 | `0.000000 (waiting)`, exit 3 | ✅ |
| 2 | `x402_balance.py 0x28C6…d60 --network ethereum` | nonzero, exit 0 | `51951.298220 (PAID)`, exit 0 | ✅ |
| 3 | `--json` | one parseable object | object with `paid:false`, `balance_raw:"0"` | ✅ |
| 4 | `--watch --interval 2 --max-polls 2` | gives up, exit 3 | 2 polls, `gave up after 2 polls`, exit 3 | ✅ |
| 5 | `--network sepolia --json` | Sepolia preset answers | `0.000000`, Base Sepolia RPC | ✅ |
| 6 | bad address | exit 1 | `error: address must be a 0x… 42-char hex string`, exit 1 | ✅ |

Verification blocks at time of testing: Base mainnet `0x31ad686`,
Ethereum mainnet `0x18e5bbb`.

## Notes

- Public RPCs (llamarpc, 1rpc, merkle, cloudflare-eth) returned 403/rate-limit
  to python-urllib user agents during testing; `eth.drpc.org` and Base's
  official endpoints answer reliably with `User-Agent: curl/8.0`, which the
  client sends by default. `--rpc` allows any private endpoint override.
- Exit-code contract (`0`/`3`/`1`) was chosen so `while ! x402-balance …; do :; done`
  and cron wrappers need zero parsing.
- Scope is intentionally narrow: balance read + watch. It does not sign
  transactions and never needs a private key.
