# Security and Key Handling

## Private keys

- Never commit private signing keys.
- Never print or paste private key contents into reports.
- Store keys outside the repository or in an approved secret manager.
- Do not overwrite an existing key unless rotation is explicitly requested.
- Trust stores contain public material only.

## Fingerprints

Use opaque IDs. Keep personal data and confidential recipient metadata outside the watermark payload.

## Evidence custody

For high-stakes investigations, preserve:

- original suspect file
- SHA-256 of every acquired artifact
- acquisition time and operator/process
- AI-IP Shield version
- engine name/version
- registry snapshot or immutable lookup record
- verification report
- attack/transformation parameters if generated during testing

AI-IP Shield produces technical evidence, not a legal admissibility determination.

## Third-party Skills

Treat Skills as executable instructions. Review any downloaded Skill before installation and do not install untrusted variants over the official repository copy.
