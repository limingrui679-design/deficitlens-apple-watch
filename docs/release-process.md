# Release process

1. Confirm the changelog, version module, package metadata, and citation version agree.
2. Run the registered public-data pipeline with unchanged default configuration.
3. Inspect aggregate results, transfer gate, case catalog, HTML report, and manifest hashes.
4. Run `python scripts/verify_release.py`; every machine-readable check must pass.
5. Run `python scripts/score_project.py`; inspect failures instead of editing the score artifact.
6. Commit the exact source and derived evidence, then build a fresh archive from that commit.
7. Extract the archive into a temporary directory and repeat the wheel smoke and safety checks.
8. Only after a real remote exists, enable CI and private vulnerability reporting, push, verify the
   remote commit, create a signed release, and add the verified URLs to metadata.

Steps 1–7 are local and reproducible. Step 8 is not completed by a local build or archive.
