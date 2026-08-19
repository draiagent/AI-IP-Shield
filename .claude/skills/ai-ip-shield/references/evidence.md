# Evidence Interpretation

## Signal roles

| Signal | What it supports | What it does not prove |
|---|---|---|
| SHA-256 match | Exact byte-for-byte integrity | Visual/semantic equivalence after transformation |
| Watermark detection | Presence of a known embedded signal | Legal ownership by itself |
| Fingerprint recovery | Association with a registered asset/copy | Who actually performed a leak |
| Registry lookup | Mapping from opaque token to controlled record | Integrity of an externally altered file |
| Trusted provenance | Signed origin/claim under the configured trust policy | That every downstream copy retained provenance |
| Do Not Train policy | Expressed training/mining preference | Technical prevention of training |

## Evidence language

Prefer:

- `NO_EVIDENCE`
- `WEAK`
- `MODERATE`
- `STRONG_SOURCE_ASSOCIATION`
- `REGISTERED_EXACT_MATCH`
- `CRYPTOGRAPHICALLY_VERIFIED`
- `CONFLICTING_EVIDENCE`

Avoid translating evidence levels into legal conclusions or percentages of guilt/ownership.

## Missing provenance

If C2PA or a sidecar is missing, report `PROVENANCE_NOT_FOUND` or the equivalent. Do not infer `FAKE` solely from absence.

## Modified files

A recovered fingerprint with a failed exact hash can still support source association while proving the current bytes differ from the registered protected file. Report both facts.
