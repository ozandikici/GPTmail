# Connect your mail accounts

GPTmail supports several mailboxes in one private workspace. Choose Google OAuth, Microsoft OAuth, or standard IMAP/SMTP credentials for each mailbox. The account's provider must permit the connection.

There are two separate OAuth connections:

- **Mail provider → GPTmail:** Lets your deployment access a Google or Microsoft mailbox. You configure the provider app described below.
- **GPTmail → ChatGPT:** Lets an MCP client use the tools you enable. This uses GPTmail's own OAuth server and does not require a Google or Microsoft app.

No shared Google/Microsoft client secret is shipped with the project. Until you configure a provider, the dashboard displays that its setup is required. Provider passwords must never be pasted into a chat, committed to GitHub, or used as OAuth client secrets.

## Deployment environment

Set these in your hosting project's **Production environment**, then redeploy. Local values belong in the ignored `.env` file.

| Variable | Needed for | Value |
|---|---|---|
| `APP_BASE_URL` | Both providers | Your exact public HTTPS origin, without a trailing slash |
| `GOOGLE_CLIENT_ID` | Google | Web application's client ID |
| `GOOGLE_CLIENT_SECRET` | Google | Web application's client secret |
| `MICROSOFT_CLIENT_ID` | Microsoft | Application (client) ID |
| `MICROSOFT_CLIENT_SECRET` | Microsoft | Client secret **value**, not its secret ID |
| `MICROSOFT_TENANT_ID` | Microsoft, optional | Defaults to `common`; use your tenant ID for a tenant-specific registration |

The encryption key and Redis settings from the [main installation guide](../README.md#3-configure-upstash--vercel) are also required. Provider refresh tokens are stored in separate encrypted Redis records. Preserve `DATA_ENCRYPTION_KEY` across redeployments.

## Gmail / Google Workspace

1. In the [Google Cloud console](https://console.cloud.google.com/), select a project you control and configure its Google Auth Platform consent/branding and audience settings. For personal testing, add the mailbox owner as a test user where required.
2. Create an OAuth client of type **Web application**. Add this exact authorized redirect URI, replacing the origin with your deployment:

   ```text
   https://your-project.vercel.app/oauth/mail/google/callback
   ```

3. Configure the requested mail scope `https://mail.google.com/`. GPTmail uses Google's IMAP/SMTP XOAUTH2 flow, which needs this broad mail scope. GPTmail's separate MCP permission switches still restrict what AI clients can do through GPTmail; they do not narrow the scope granted at Google.
4. Save the client ID and secret in `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`; redeploy.
5. Log in to your GPTmail dashboard, choose Google, enter the mailbox address, and complete Google's consent page. Only enter the Google password on Google's own sign-in page.

GPTmail requests offline access for token refresh and validates the mailbox by authenticating to IMAP before saving it. Workspace administrators may limit third-party app access. Google consent and verification requirements depend on the app audience and scopes; a public GitHub repository is not Google verification. An external app in **Testing** can have short-lived authorizations, including seven-day refresh-token expiry for the mail scope. Review the audience before relying on a persistent connection.

Sources: [Google web-server OAuth setup](https://developers.google.com/identity/protocols/oauth2/web-server), [Gmail XOAUTH2 and mail scope](https://developers.google.com/workspace/gmail/imap/xoauth2-protocol), [Google app audience and testing limits](https://support.google.com/cloud/answer/15549945).

## Outlook.com / Microsoft 365

1. In the [Microsoft Entra admin center](https://entra.microsoft.com/), create an app registration you control. Choose supported account types that match your mailboxes. A registration intended for both personal Outlook.com and organizational accounts must include both account types; tenant policy can still restrict organizational access.
2. Add a **Web** platform redirect URI matching your deployment exactly:

   ```text
   https://your-project.vercel.app/oauth/mail/microsoft/callback
   ```

3. Configure the delegated Exchange Online mail permissions needed by the app. GPTmail requests:

   ```text
   https://outlook.office.com/IMAP.AccessAsUser.All
   https://outlook.office.com/SMTP.Send
   offline_access
   ```

   These are IMAP/SMTP permissions, not Microsoft Graph `Mail.Read` / `Mail.Send`. Admin consent may be required by the organization.
4. Create a client secret and save its **value** in `MICROSOFT_CLIENT_SECRET`; set `MICROSOFT_CLIENT_ID`. Set `MICROSOFT_TENANT_ID` if your registration needs a specific tenant; otherwise GPTmail uses `common`. Redeploy.
5. In GPTmail, choose Microsoft, enter the mailbox address and finish Microsoft's consent flow.

The mailbox must have IMAP enabled. SMTP AUTH can be disabled by organization or mailbox policy even when IMAP works. GPTmail checks SMTP authentication without sending a test message. If SMTP is unavailable, an otherwise valid OAuth mailbox can remain connected for reading; sending will not become available merely because you turn on GPTmail's Send permission. Review the provider's policy with the mailbox administrator rather than assuming every account can send.

Source: [Microsoft's IMAP/SMTP OAuth setup and scopes](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth).

## Other providers and custom domains

Use **IMAP/SMTP** in the account form for providers that support password or app-password access. Enter the provider's documented server names, ports and usernames. IMAP uses TLS; SMTP uses TLS or mandatory STARTTLS. A provider preset is a starting point, not proof that the account's plan or policy permits access.

iCloud, Yahoo, Zoho and domain mail services can fit this model when the account allows IMAP and supplies compatible credentials. Add an app password when the provider requires one. Mailboxes without accessible IMAP/SMTP need a separate integration. Local desktop bridges, including a bridge reachable only at `localhost`, are not directly reachable from a Vercel deployment. No direct Proton Mail or Tuta integration is included.

Preset references: [Apple iCloud](https://support.apple.com/en-ie/102525), [Yahoo Mail](https://help.yahoo.com/kb/new-yahoo-mail/imap-server-settings-yahoo-mail-sln4075.html), [Zoho Mail](https://www.zoho.com/mail/help/imap-access.html), [Fastmail](https://www.fastmail.help/hc/en-us/articles/1500000278342-Server-names-and-ports). Zoho region and organization settings can differ; Fastmail requires an app password and a plan that includes IMAP.

## Connection checks and troubleshooting

| What you see | What to check |
|---|---|
| Provider setup required | Both client variables are present in the active environment and the app was redeployed |
| Redirect URI mismatch | The provider registration, `APP_BASE_URL`, HTTPS scheme and callback path match exactly |
| Consent refused / administrator approval needed | Provider audience, test-user membership, granted scopes and organization policy |
| OAuth succeeds but account is not saved | IMAP availability and whether the entered address belongs to the authorized mailbox |
| Account reads but cannot send | SMTP status, SMTP AUTH policy and GPTmail's Send/Reply permissions |
| Reconnect required | Provider authorization was revoked or expired; use the account's OAuth connection flow again |

Removing an account deletes its saved credentials from GPTmail. To revoke the provider's grant as well, use the provider's connected-app settings. Revoking **ChatGPT/MCP access** in GPTmail is a separate action and does not revoke Google or Microsoft consent.

## What has been verified

Provider integration code is tested with isolated automated tests. Real mailbox access still needs a live provider app registration, owner consent and an account-specific connection check. No live Gmail, Outlook or generic IMAP mailbox was connected as part of this release's setup. Do not advertise a provider as live-tested until that test is actually completed.

## Türkçe kısa özet

Google veya Microsoft ile bağlanmak için önce kendi sağlayıcı uygulama kaydını oluştur ve yukarıdaki ortam değişkenlerini Vercel'e ekle. Callback adresi sitenin gerçek adresiyle birebir aynı olmalı. Ardından yeniden dağıt, GPTmail'e yönetici parolanla gir ve **Hesaplar** bölümünden sağlayıcıyı seç.

Diğer servislerde sağlayıcının IMAP/SMTP bilgilerini ve gerekiyorsa uygulama parolasını kullan. Her posta kutusu ayrı eklenir. Google/Microsoft kurumsal politikaları, IMAP erişimi ve SMTP gönderim izni geçerliliğini korur; uygulama bunları aşmaz. Parolaları ve client secret değerlerini sohbete veya GitHub'a yazma.
