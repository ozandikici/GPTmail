# Security policy

GPTmail is self-hosted software that may have access to highly sensitive email and credentials. **Do not submit vulnerabilities containing real secrets, private messages or tokens as public GitHub issues.** When the GitHub repository is published, use its private security advisory reporting channel if enabled, or contact the repository maintainer through a private, mutually agreed channel.

## Guidance

- Never commit `.env` or place mail passwords/API keys in GitHub Issues, PR descriptions, screenshots, build logs or AI chat prompts.
- Use a unique owner password (minimum 12 characters, recommended 16+) and provider app passwords with limited scope if supported.
- Require TLS for IMAP and SMTP, and configure a real HTTPS `APP_BASE_URL` for the deployed MCP endpoint.
- Review each requested permission in GPTmail. Leave send/delete approvals enabled until you understand the risks of autonomous AI actions.
- Content obtained from emails, including HTML or attachments, is **untrusted input** and can attempt prompt injection against an AI client.
- If compromised, revoke all OAuth tokens from the dashboard, rotate provider app passwords, rotate the admin password hash, and consider replacing Upstash credentials. Rotate the Fernet key only after deliberately clearing or migrating encrypted data.
- Verify third-party dependency advisories before exposing an instance to the public Internet.

## Known non-goals

This application targets a **single trusted owner**. It is not audited as a multi-tenant SaaS, doesn't permanently expunge mail, and doesn't provide antivirus scanning for attachments. Gmail/Microsoft provider OAuth requires owner-managed application registrations; provider tokens are encrypted at rest and never returned to the dashboard or MCP client. Provider integration tests use mocked services until an owner configures and authorizes a real mailbox. The open-source repository may be public, but individual deployments are expected to be private.

The dashboard's “revoke MCP connections” action revokes AI-client access, not the provider grant. Remove the mailbox in GPTmail and revoke its application access in Google/Microsoft account settings when you want to end provider authorization.
