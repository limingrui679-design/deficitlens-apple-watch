# Security and health-data disclosure

## Supported versions

| Version | Security fixes |
|---|---|
| 1.1.x | Supported after public release |
| 1.0.x | Upgrade required |

DeficitLens is currently a locally verified release candidate, not a published service. No hosted
application, telemetry endpoint, account system, or public vulnerability channel exists.

## Reporting

Do not open a public issue containing Apple Health data, credentials, exact routes, identifying
timestamps, device identifiers, or a working exploit. A private vulnerability-reporting channel
must be enabled in the eventual repository before public support is announced. Until then, do not
transmit sensitive material unless you already have a trusted private contact with the maintainer.

When a channel exists, include the affected version, minimal reproduction using synthetic data,
impact, and suggested embargo needs. Maintainers should acknowledge a complete report within five
business days, publish a severity and remediation decision, and credit the reporter if requested.
These are response targets, not evidence that a response team currently exists.

## Health-data incidents

If private data or a credential was committed, stop distribution, rotate exposed credentials,
identify every affected ref and release, use an appropriate history-rewrite incident process, and
assume existing clones retain the material. Do not ask a reporter to upload a real Health export.

The local release gate scans tracked files for high-confidence secrets, private export names,
absolute home paths, and unsafe archives. It reduces accidental disclosure risk; it is not a
penetration test or a guarantee that a repository is free of vulnerabilities.
