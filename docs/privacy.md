# Privacy and threat model

Apple Health exports can contain years of highly sensitive records, exact timestamps, routes,
device names, and identifiers. DeficitLens assumes the local machine and chosen output directory
are trusted; it does not assume a Git repository, cloud-sync folder, notebook, or terminal log is
private.

## Defaults

- XML is parsed locally with `defusedxml` iterative parsing; no network call is made.
- Apple Watch-only filtering is enabled.
- Source names are salted with a fresh random per-run value and hashed in memory.
- Only daily/workout aggregates, scenario tables, and a self-contained report are written by the
  public CLI.
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

## Salt and expert row export

The default salt is randomly generated for each parse, so hashes cannot be joined across runs.
Callers that need stable local joins may pass their own high-entropy salt through the Python API;
the public CLI does not expose one. Hashing is pseudonymization, not anonymization.

The expert Python row writer contains exact timestamps and stable hashes. It raises
`PermissionError` unless the caller passes `acknowledge_sensitive_output=True`. This guard makes
the boundary explicit; it cannot stop a caller from writing or sharing sensitive data after
acknowledgement.

Entity expansion and DTD-based XML attacks are rejected. Parsing remains a local-data operation,
not a complete malware sandbox, so exports should still come from a trusted device.
