# Development guide

English | [Simplified Chinese](docs/zh_cn/CONTRIBUTING.md)

Start with the [README](README.md), [development record](DEVELOPMENT_LOG.md) and [validation record](docs/VALIDATION.md). Do not read or print local nas-session content or put raw HAR captures, accounts, passwords or SIDs in tests or distributions.

## Environment and checks

Create a virtual environment with Python 3.11+ and run `python -m pip install -e '.[dev]'`. Then run:

```sh
python tests/run_regression.py
python -m pytest --cov=qnap_sdk --cov-report=term-missing --cov-report=xml:reports/coverage.xml
python -m ruff format --check qnap_sdk tests examples scripts
python -m ruff check qnap_sdk tests examples scripts
python -m build
python -m twine check dist/*
python scripts/check_release.py --dist dist
```

The offline runner forbids network connections and subprocesses. Default pytest discovery includes only `test_*.py`, so live runners do not run automatically. Tests should exercise behavior, failures, readback or actual wire contracts; ordinary tests must not make remote mutations.

## Architecture and firmware support

- `client.py`: origin restrictions, transport, response parsing, contract execution and mutation readback.
- `auth.py`: native authentication, session checks, NAS logout and revocation verification.
- `resources.py` / `models.py`: public resource APIs, pagination and result models.
- `profile.py` / `profiles/*.json`: firmware contracts installed with the package.
- `session.py` / `cli.py`: explicit session persistence and command-line access.
- `browser_transport.py` / `dashboard.py`: optional local bridge tools; the core SDK does not require a browser.

Bundled profile JSON files define distribution contracts. `discovery/endpoints.json` mirrors the existing contract for older discovery tools. Update both copies together; tests verify equality. New firmware requires a separate JSON file registered in `profile.PROFILES`. Never claim compatibility by changing a version string. Record method/path, query versus form placement, success/failure fields, model mappings, evidence and read-only verification.

First inspect endpoints already used by the authorized device's frontend, then confirm read-only behavior. Mutations must use explicitly authorized test resources. Check collisions before creating users, groups or shared folders; record the baseline and clean up only resources created by the test in `finally`. Inspect state after a failure instead of blindly retrying a write. Test password changes only on synthetic accounts.

Historical test authorization and evidence are recorded in the development log. For future work, use the current conversation's authorization to determine whether clarification is needed. Administrator login should use hidden input or an independent login window; do not collect passwords in chat.

## Examples and distribution verification

[read_only.py](examples/read_only.py) demonstrates login and inventory queries. [session_usage.py](examples/session_usage.py) demonstrates explicit SID persistence and logout. Both require command-line arguments and do not connect on import. The README includes resource-management examples.

After building, create a clean environment outside the project and install the wheel with `pip install --no-deps /absolute/path/to/wheel`. Verify imports, `get_profile()` and the three offline CLI commands without relying on `discovery/` or the development workspace. Extract and rebuild the sdist as well. Check archives for work directories, reports, sessions, raw captures and caches.

Keep versions synchronized in `pyproject.toml` and `qnap_sdk/__init__.py`; update the [changelog](CHANGELOG.md) and development record. Use the MIT license and the real repository URL. See the [PyPI publishing guide](docs/PUBLISHING.md) for the configured release workflow. Version 0.4.0 has already been published; never reuse an uploaded version.

## Documentation languages

English is the default for the root Markdown documents and `docs/`. Chinese translations live in `README-zh_cn.md` and `docs/zh_cn/`. Update both languages together, preserve code examples and API identifiers, and keep language switches and relative links valid. Include the Chinese README and translated guides in the source distribution. Documentation updates on GitHub do not replace README metadata in an already published PyPI version; it updates with the next release.
