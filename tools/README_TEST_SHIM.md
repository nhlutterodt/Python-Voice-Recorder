VOICE_RECORDER Test Shim
========================

Purpose
-------
This small helper (`sitecustomize.py`) exists to make running the test suite against
the in-repo canonical package layout (`voice_recorder.*`) compatible with existing
tests that still import or patch legacy top-level module names like
`services.file_storage...`.

Important: this is a dev/test convenience only. Do NOT add this file to any
packaging or production runtime. The shim is gated by an environment variable
and should be enabled only in test runners (local dev and CI) when needed.

How it works
------------
- If the environment variable `VOICE_RECORDER_TEST_SHIM` is set to `1`, `true`,
  or `yes`, `tools/sitecustomize.py` will run at Python startup (when `tools`
  is on `PYTHONPATH`) and it will alias a small set of legacy module names to
  their canonical `voice_recorder.*` equivalents in `sys.modules`.

Recommended long-term approach (professional)
--------------------------------------------
1. Keep the compatibility shim out of the package namespace. Leave it under
   `tools/` so packaging and runtime environments are unaffected.
2. Gate the shim behind the environment variable `VOICE_RECORDER_TEST_SHIM`.
3. Update CI to enable the shim only for the test job(s) that need it. For
   example, in GitHub Actions add the `tools` dir to `PYTHONPATH` and set the
   env var for the test step.
4. Concurrently, plan to migrate tests to import the canonical `voice_recorder.*`
   names. The shim should be temporary and removed after tests are updated.

Example CI (PowerShell) snippet
-------------------------------
Add this to the test step in your workflow when running on Windows/PowerShell:

```powershell
$env:VOICE_RECORDER_TEST_SHIM = '1'
$env:PYTHONPATH = "${{ github.workspace }}\tools;${{ github.workspace }}\Python - Voice Recorder\src;${{ github.workspace }}"
pytest -q
```

Local usage
-----------
- Run tests locally with the shim enabled (PowerShell):

```powershell
$env:VOICE_RECORDER_TEST_SHIM = '1'
$env:PYTHONPATH='C:\path\to\repo\tools;C:\path\to\repo\Python - Voice Recorder\src;C:\path\to\repo'
pytest -q -k "services or utilities"
```

Removal plan
------------
- Start migrating tests to canonical imports. Prefer small PRs that update tests
  touching one package area at a time.
- When the repository no longer contains tests that import or patch legacy
  top-level module names, remove `tools/sitecustomize.py` entirely.

Questions
---------
If you'd like, I can:
- Open a PR that adds this README and the gated shim (already in the branch),
- Update CI workflow files to enable the shim for test steps, or
- Start migrating tests to canonical imports in small batches.
