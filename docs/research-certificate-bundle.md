# The certificate update covers Python's default bundled trust, not every connection

## Verified on 21 October 2026

This checkout uses `pyproject.toml` and `uv.lock`, not `requirements.txt`.
The previous lock contained certifi 2025.10.5. The project now requires
`certifi>=2026.10.19`, including in built package metadata, and locks 2026.10.19.
This floor prevents a normal pip/uv resolver from selecting an older certifi
when installing this updated source or its wheel. No other third-party package
versions were changed. Lock regeneration also reconciled the existing project
version (3.0.1) with stale lock metadata (3.0.0) and updated the lock schema revision.

Official sources checked:

- [PyPI release metadata](https://pypi.org/pypi/certifi/2026.10.19/json):
  2026.10.19 was the latest non-yanked release when checked; requires Python >=3.7.
  Both files were uploaded on 20 October 2026 UTC (the version date is 19 October).
- [GitHub tag](https://github.com/certifi/python-certifi/tree/2026.10.19):
  tag object `39e296825d323aa1c8e998ffd9cc57fe22514a24`, commit
  `662df63d7906df66f1f07c0751a3dfe9da14d914`.
  GitHub's tag API reported `verified=false`, reason `bad_cert`; no independently
  verified tag-signature claim is made. The release REST endpoint returned 404;
  tag existence and contents were verified separately.
- [Maintainer explanation](https://github.com/certifi/python-certifi/issues/439):
  the mitigation removes roots rather than implementing intermediate revocation.
  The tagged commit restores unaffected emSign roots; do not interpret this
  release as removing every emSign root.
- [uv 0.13.4 advisory](https://github.com/astral-sh/uv/security/advisories/GHSA-hq85-5cpj-mr62):
  installer trust is a separate update from application trust.

Downloaded wheel and sdist SHA-256 values matched official PyPI metadata:

| Artifact | SHA-256 |
| --- | --- |
| certifi-2026.10.19-py3-none-any.whl | `42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b` |
| certifi-2026.10.19.tar.gz | `035c1e85572b141bf1c3a3eff0e33a8eb74917522f2559075ff8d2fea780a1ae` |

The wheel's `cacert.pem` was byte-identical to the GitHub tag's file and to the
installed environment's bundle, SHA-256
`50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`.
Its parsed trust anchors exclude **emSign ECC Root CA - G3** and
**AAA Certificate Services**. Other emSign roots remain.

## Installer compatibility

`pyproject.toml` enforces **uv >=0.13.4** with `tool.uv.required-version`.
This is the tested installer floor for the revision-5 lock and the separate
installer trust update. Local uv 0.11.25 was verified to report a clear version-requirement error
instead of proceeding with an unsupported lockfile. Follow the
[source installation guide](installation-from-source.md) to upgrade intentionally.

The repository's `publish.yml` and `publish_pypi.yml` workflows use unpinned
`pipx install uv`; the devcontainer uses unpinned `pip install ... uv`, and the
installation Dockerfiles use the current uv shell installer. No incompatible
pinned uv version was found in those paths or the installation documentation.
Existing cached/local installations still need the explicit upgrade.

## Actual protection boundary

The locked dependency graph includes HTTPX and Requests. Offline tests confirm
their default configurations use the installed certifi bundle with certificate
verification enabled. This does not establish which HTTP calls an operator's
specific deployment performs or which overrides it applies.

No certificate-verification disabling or CA-path overrides were found in the
tracked application/configuration sources inspected. Runtime environment values
and deployment secrets were not inspected. Audit `SSL_CERT_FILE`, `SSL_CERT_DIR`,
`REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`, custom SSL contexts/adapters and proxy trust
separately. OS stores, Python/OpenSSL, the installer's own trust store and other
processes are not patched by this dependency change. Never disable verification
to work around a failing chain. Root removal is not an eight-intermediate SPKI
blocklist; alternate trust paths and legitimate-chain breakage need separate review.

`ros_mcp/utils/websocket.py` constructs **plain `ws://`** rosbridge connections.
Certifi does not encrypt or authenticate those connections. The default MCP
transport is stdio; HTTP server examples do not automatically acquire TLS from
this change. Network isolation and a separately reviewed secure transport remain
operator responsibilities; no transport redesign was included here.

## Apply only after review and authorized rollout

1. Use a patched installer (uv >=0.13.4 for the cited installer advisory) in the
   approved deployment workflow; updating the installer alone does not patch the app.
2. Source deployments: install the reviewed source and run `uv sync --locked`
   in each target environment. Wheel/pip deployments: rebuild and install the
   reviewed wheel with dependency resolution enabled. Do not use `--no-deps` or
   stale constraints that defeat the security floor.
3. Published `uvx ros-mcp` installs and cached tool environments do **not** consume
   this local checkout's edits. A reviewed release/explicit approved source install
   and refresh of each relevant environment are still required. Nothing was
   published or deployed as part of this change.
4. Rebuild affected images and restart the relevant MCP/LLM client processes after
   upgrading: already-created SSL contexts and sessions can retain old trust.
5. In each actual application environment, record `certifi.__version__`,
   `certifi.where()`, the bundle hash and the effective client trust configuration.
   Validate legitimate upstream chains through that actual path under separate
   authorization; a browser/curl success is not an application TLS attestation.

## Safe local regression checks

```bash
uv sync --locked --extra dev
uv run --locked pytest tests/test_certificate_bundle.py
uv pip check
```

The four tests cover installed dependency metadata/version, the absence of the
emSign ECC Root CA - G3 DER SHA-256 fingerprint
`86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b`
and bundle parsing, Requests defaults, and HTTPX context construction. AAA root
absence is descriptive evidence above, not an unrelated regression requirement.
They make no requests, start no server and require no robot or ROS installation.

Validated on macOS arm64 / Python 3.10.20 with a task-local uv 0.13.4:
locked editable installation and separately built-wheel installation both passed
all four tests and dependency checks. Full Ruff checks/format checks passed.
CLI `--help` passed with socket connection functions blocked. Only certifi's
third-party lock entry changed; official artifact URLs, sizes and hashes matched.

Docker/git installation tests were not run: git-based tests target remote source,
not these uncommitted changes. Linux/Windows and other Python versions remain
unverified. ROS integration, devices, graphs, production services, real upstream
TLS handshakes and deployments were deliberately not exercised.

Review follow-up: the changed G3 fingerprint test passed independently after the
initial four-test editable/wheel runs. Its targeted Ruff checks passed. uv 0.13.4
passed lock validation and locked sync with the enforced minimum; uv 0.11.25
exited 2 with the explicit version mismatch. Unaffected tests were not repeated.
The [official required-version setting](https://docs.astral.sh/uv/reference/settings/#required-version)
documents the enforcement used here.
