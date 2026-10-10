# GPTmail

**Your mail. Your rules.** A self-hosted, open-source IMAP/SMTP mailbox and authenticated remote MCP server for ChatGPT and other compatible MCP clients.

GPTmail lets you manage email accounts from a browser, search and read mail, and selectively enable AI actions such as sending, replying, forwarding, flagging, moving and trashing messages. **Each MCP capability is controlled from the dashboard.** Outgoing mail and Trash actions optionally require a second approval in the dashboard; both approval switches are **ON** by default.

- **Free-tier-friendly:** FastAPI on Vercel + a persistent Upstash Redis database (check each service's current terms and quotas).
- **Cross-provider:** IMAP over TLS and SMTP over TLS/STARTTLS, without vendor-specific mail APIs.
- **Encrypted credentials:** IMAP/SMTP account records and pending outbound drafts encrypted with Fernet before storage.
- **Remote MCP:** Streamable HTTP at `/mcp`, compatible with MCP 2025 and the 2026-07-28 stateless revision.
- **OAuth:** Authorization Code + PKCE (S256), Dynamic Client Registration, scoped owner consent, bearer tokens and rotating refresh tokens.
- **Single-owner:** A password-protected private admin dashboard. Your public **source code** does not make your deployed mailbox public.
- **MIT licensed.** Python, HTML, CSS and vanilla JavaScript; no OpenAI API key required.

> **Safety note:** IMAP/SMTP passwords remain on your server and in encrypted server-side storage, but **email content you ask ChatGPT to read is sent to ChatGPT**. Mail contents are untrusted third-party data and must never be followed as instructions. SMTP send permissions are initially off. This is a single-owner personal deployment template, not a production multi-tenant email service.

[Türkçe kurulum rehberi →](docs/README.tr.md)

## Available MCP tools

| Capability in dashboard | Tools | Initial state |
|---|---|---|
| Read | `list_accounts`, `list_folders`, `list_messages`, `search_messages`, `read_message` | **On** |
| Attachments | `get_attachment` (max 2 MB) | Off |
| Send | `send_email` | Off |
| Reply | `reply_email` | Off |
| Forward | `forward_email` (text only, no forwarded attachments) | Off |
| Drafts | `save_draft` | Off |
| Flags | `mark_message` | Off |
| Move and archive | `move_message`, `archive_message` | Off |
| Delete | `delete_message` (moves to Trash, never permanently expunges) | Off |
| Create folder | `create_folder` | Off |

Approval switches are separate: `send_approval = true` and `delete_approval = true` by default. Turning those switches **off** allows enabled tools to execute directly, subject to ChatGPT's own confirmation/permission settings. The dashboard owner can also manage their own mail manually, independently of the MCP policy.

## 1. Prerequisites

- A GitHub account and a Vercel account with access to an appropriate deployment plan.
- An Upstash Redis database with its **REST** URL and **read/write** REST token. The [Vercel marketplace integration](https://vercel.com/marketplace/upstash) can set these environment variables for you.
- Python 3.11+ to generate secrets, or a local Python setup.
- An IMAP mailbox with SSL/TLS access, and SMTP access if you want outbound mail. Some providers require an **app password** or an alternate authentication mechanism; GPTmail currently implements **username/password IMAP and SMTP**, not Gmail or Outlook OAuth sign-in.

## 2. Create the public GitHub repository

Create an empty **public** repository named `GPTmail` in your GitHub account. Add the contents of this project; **do not commit `.env`**. For the authenticated `ozandikici` account, the included publishing helper can do this in one step **if GitHub CLI (`gh`) and Git are installed**:

```powershell
# Windows PowerShell, from the GPTmail folder
./scripts/publish_github.ps1
```

```bash
# Linux / macOS, from the GPTmail folder
bash scripts/publish_github.sh
```

First run `gh auth login`. The script creates `ozandikici/GPTmail` as a public repo; if you are publishing under a different username, change the target owner in the script. Alternatively, create the repository manually and run:

```bash
cd GPTmail
git init
git branch -M main
git add .
git commit -m "feat: initial GPTmail open-source release"
git remote add origin https://github.com/ozandikici/GPTmail.git
git push -u origin main
```

If GitHub creates an initial README on its own, reconcile that commit before pushing (or create an **empty** repo).

## 3. Configure Upstash + Vercel

1. Import the GitHub repository into [Vercel](https://vercel.com/new). Vercel recognizes the root-level `app.py` FastAPI application without a `vercel.json` file.
2. Create a free-tier-compatible Upstash Redis database and connect it to the Vercel project, or set the REST credentials yourself.
3. Generate a strong password hash and encryption key **locally**:

   ```bash
   python -m pip install -r requirements.txt
   python scripts/make_secrets.py
   ```

4. Set the following **Vercel project Environment Variables** (Production environment):

   | Variable | Example / meaning |
   |---|---|
   | `APP_BASE_URL` | `https://your-project.vercel.app` (exact production URL, **no trailing slash**) |
   | `ADMIN_PASSWORD_HASH` | Output from `scripts/make_secrets.py` |
   | `DATA_ENCRYPTION_KEY` | Output from `scripts/make_secrets.py` |
   | `UPSTASH_REDIS_REST_URL` | Upstash REST HTTPS endpoint |
   | `UPSTASH_REDIS_REST_TOKEN` | Upstash **read/write** REST token |

5. Deploy/redeploy after setting the variables. If the production URL is not known until the first deployment, set/update `APP_BASE_URL` after that deployment and redeploy.
6. Open the deployed app and log in using the **original password** you chose when generating `ADMIN_PASSWORD_HASH`.
7. Add your account under **Accounts**. The server verifies IMAP and (if entered) SMTP before saving encrypted credentials.

> Keep `DATA_ENCRYPTION_KEY` unchanged across redeployments: changing it makes existing encrypted account entries and pending requests unreadable. You can intentionally rotate it after first removing/re-adding all mail accounts.

## 4. Connect ChatGPT

The MCP endpoint is:

```
https://your-project.vercel.app/mcp
```

In a ChatGPT workspace that supports custom/private remote MCP plugins, add a custom connection with this HTTPS server URL and choose OAuth authorization. ChatGPT discovers `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource` metadata, registers a public OAuth client (DCR), and redirects to GPTmail for one-owner authorization. Enter your GPTmail admin password and consent to the connection. The password is not shared with ChatGPT.

Once linked, use prompts such as:

- “List the accounts available in GPTmail, then summarize my 10 newest emails.”
- “Search my company mailbox for the latest inspection documents.”
- “Prepare a reply to this email and ask me before sending it.”

Enable **Reply** or **Send** in the GPTmail permissions tab before attempting write actions. When **Send approval** is on, the MCP tool queues an outgoing message and the dashboard owner must explicitly approve it. The model cannot silently bypass the server-side check. After modifying permissions, the ChatGPT tool list may need to be refreshed or the connection reloaded.

Custom MCP/plugin availability depends on ChatGPT account/workspace permissions; deployment alone does not install the plugin into your ChatGPT account. This repository is an MCP server, not a published ChatGPT Plugin Directory listing.

## Run locally

```bash
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env and edit it with real values
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Visit `http://localhost:8000`. Local mode still requires an Upstash database for persistence. `localhost` is **not** reachable from ChatGPT's cloud connection: deploy to HTTPS for remote MCP use.

## Security model and known limitations

- **Secrets:** No credentials, token values, message content, subject lines or recipients are stored in the audit log. Raw mailbox credentials are encrypted with a server-owned encryption key and never returned in dashboard state or MCP tool responses.
- **Authentication:** No anonymous MCP tools. OAuth access tokens live 1 hour; refresh tokens live 30 days and are one-time/rotating. Revoke all connected clients from the dashboard to invalidate all older access and refresh tokens.
- **Authorization:** The server checks the current permission **again on every tool call**; cached client-side tool lists do not override current policy. Queued actions must also pass permission checks at approval time.
- **Safer deletion:** Delete means *move to Trash*, not permanent removal. Moving requires IMAP `MOVE` support; insecure `EXPUNGE` fallbacks are deliberately avoided.
- **Message limits:** Individual messages over 14 MB are not read; retrieved attachment payloads are capped at 2 MB; displayed body text at 25,000 characters; outbound plain-text bodies at 80,000 characters; max 20 recipients. Forwarding only includes original text, **not original attachments**.
- **No OAuth login to Google/Microsoft:** Mail providers enforcing OAuth-only IMAP or disabling app passwords are not supported by this release.
- **OAuth:** DCR + S256 PKCE, no CIMD advertisement. Owner password entered only into the self-hosted authorization page. Custom OAuth is intentionally minimal and should undergo external security review before public multi-user SaaS deployment.
- **Rate limits:** OAuth endpoints and outgoing mail operations are rate-limited. Serverless database access and mail calls rely on external network availability.
- **Costs:** GitHub's public repository hosting can be free; Vercel Hobby has usage/acceptable-use limits; Upstash has a free tier with quotas. Review their current plan terms before commercial or high-volume use.
- **Testing:** Automated tests cover owner sessions, OAuth/PKCE, protocol responses, permission defaults and input validation. **No live IMAP/SMTP account or live ChatGPT installation has been tested by this project template.**

## Development

```bash
pip install -r requirements.txt pytest httpx
pytest -q
```

PRs and security improvements are welcome. See [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT © 2026 GPTmail contributors.
