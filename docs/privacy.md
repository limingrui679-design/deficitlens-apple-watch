# Privacy and threat model

Apple Health exports can contain years of highly sensitive records, exact timestamps, routes,
device names, and identifiers. DeficitLens assumes the local machine and chosen output directory
are trusted; it does not assume a Git repository, cloud-sync folder, notebook, or terminal log is
private.

## Defaults

- XML is parsed locally with iterative parsing; no network call is made.
- Apple Watch-only filtering is enabled.
- Source names are salted and hashed in memory.
- Only daily aggregates and scenario tables are written by the public CLI.
- Raw normalized records, exact timestamps, record IDs, and device strings are not written.
- Common Health export names, raw data folders, SQLite files, and archives are gitignored.
- Public benchmark manifests record only source filenames and checksums, never absolute local
  paths.

## Residual risks

Daily aggregates can still reveal exercise patterns. Small files may be captured by backups,
shell history, or cloud synchronization. A user who passes `--include-non-watch` expands source
scope. `--keep-source-names` disables in-memory redaction and should be used only for debugging.

Before sharing an audit, inspect every file in the chosen output folder. Delete it with an
appropriate secure/local workflow if it is no longer required. DeficitLens never deletes input
or output automatically.

## Salt management

Set `DEFICITLENS_HASH_SALT` to a private random value if stable local source hashes are needed.
The default `local-only` salt prevents cleartext leakage but is not resistant to a determined
dictionary attack and must not be presented as anonymization.
