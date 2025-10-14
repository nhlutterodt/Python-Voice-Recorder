# Google OAuth setup for Voice Recorder Pro (developer/dev testing)

This document describes the minimal steps to configure Google Sign-in for local development and testing of Voice Recorder Pro.

1) Create an OAuth 2.0 Client ID
- Go to https://console.cloud.google.com/
- Select or create a project.
- Open "APIs & Services" → "OAuth consent screen" and configure a testing consent screen. Add yourself as a test user if the app is in testing mode.
- Under "APIs & Services" → "Credentials", click "Create Credentials" → "OAuth client ID".
- Choose "Desktop app" (recommended for the installed-app loopback flow) or "Web application" if you want a fixed redirect. For local dev, "Desktop app" is simplest.
- If you choose "Web application", add the loopback redirect origin(s) you'll use during testing. For the loopback flow (recommended), you can use the loopback redirect URI pattern (the library will use http://127.0.0.1:<ephemeral-port> by default).

2) Download client_secrets.json
- After creating the Client ID, download the JSON and place it at `config/client_secrets.json` in the repository root (i.e. next to `config/presets.json`).
- If you prefer not to check secrets into source control, keep the file outside the repo and set an environment variable `VRP_CLIENT_SECRETS` with the absolute path to the file. (We can add support for this env var on request.)

3) Required APIs and scopes
- Enable the Google Drive API in the same project if you plan to interact with Drive. In the console, go to "APIs & Services" → "Library" and enable "Google Drive API".

4) Redirect URIs and desktop loopback flow
- The code in `cloud/auth_manager.py` uses the loopback flow. It starts a local server on `127.0.0.1` with an ephemeral port and sets the redirect URI to `http://127.0.0.1:<port>`.
- For the Google Console, when using the "Desktop app" credential, you do not have to pre-register the loopback port. Desktop client credentials are allowed to use loopback redirect URIs.

5) Publish/Testing considerations
- If your OAuth consent screen is in "Testing" mode, add any Gmail accounts you will sign in with as test users. If you need the app to be available to all users, publish the consent screen (requires describing scopes and may require a verification process for sensitive scopes).

6) Troubleshooting
- If you see logs like `Google APIs not available for authentication` it means the required Python libraries are not installed in your venv. Install the runtime deps with:

  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

- If you see `No Google OAuth client configuration found.`, ensure `config/client_secrets.json` exists and is a valid JSON downloaded from the Google Console.
- If authentication opens the browser but the callback never returns, check that the local firewall or security software is not blocking connections to 127.0.0.1.

7) Optional: Add a `client_secrets.json` example
- See `config/client_secrets.json.example` for the structure expected by the app.

If you'd like, I can add support for an environment variable to override the client secrets path, or add a quick command that validates the client_secrets file and exercises the OAuth Flow to the point of opening the browser (without completing the full exchange). Tell me which option you prefer and I will implement it.
