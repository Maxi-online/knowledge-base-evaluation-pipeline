# Publication and runtime data boundaries

This portfolio release contains source, neutral configuration and fictional examples. It excludes original client corpora, vector caches, generated conversations, credentials, private contacts and deployment-specific callback URLs.

## Checks included in this repository

- english_guard.py checks tracked prose, comments, docstrings, messages and filenames. No broad source-directory exceptions are configured.
- publication_guard.py checks Python credential literals, configuration values and fingerprints of removed private identifiers. Configuration includes INI-style .config files.
- The secret-scan workflow uses a pinned Gitleaks release with a verified archive checksum. It scans current files and reachable Git history without trusting repository ignore annotations as secret exceptions.
- Offline tests remove provider credentials, replace model/integration adapters and block external connections. Local event-loop control channels are permitted on Windows.

Pattern checks and fingerprints are regression controls, not proof that every unknown secret format or private business fact can be detected automatically. Review any new corpus, configuration, binary artifact or generated output before committing it.

## Runtime settings

Supply real credentials only through the operator's process environment or an ignored local configuration mechanism. .env.example contains names and neutral settings, never working credentials. The application must not receive a provider credential in a user request body.

Generated state and corpora belong outside tracked source, normally under var/. Do not commit SQLite stores, FAISS files, pickle caches, learner answers, contact exports or client documents. Docker build contexts exclude local credentials and generated state as well.

Use an identity-aware gateway before exposing the APIs to end users. Shared operator tokens do not provide independent tenant/user authorization. Disable raw access logging for callback routes that carry provider channel tokens in their URL.

## Reporting

Do not paste credentials, private documents or contact records into public issues or pull requests. Use a private repository security report where available. If a real credential has been exposed, revoke or rotate it through its provider; removing a current file alone does not remove old commits, copies or cached content.

## Rights

Public visibility permits portfolio inspection under LICENSE. It does not grant unrestricted use, redistribution or deployment rights. Third-party dependencies remain subject to their own licenses.
