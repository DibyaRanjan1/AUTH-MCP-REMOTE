# Auth MCP Server

A remote MCP (Model Context Protocol) server protected by Auth0 OAuth. It exposes tools for the authenticated user (greet, writing prompts) and optional Gmail access (list recent emails for the logged-in user).

---

## Prerequisites

- **Python 3.13+**
- **uv** ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Auth0 account** (for MCP authentication)
- **Google Cloud project** (only if you want Gmail tools)

---

## End-to-end setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd auth-mcp-remote
uv sync
```

### 2. Auth0 setup (required)

You need an Auth0 Application and API so MCP clients can authenticate.

1. **Create an Auth0 account** at [auth0.com](https://auth0.com) and open the **Dashboard**.

2. **Create an API** (this is your “audience”):
   - **Applications** → **APIs** → **Create API**
   - Name: e.g. `Auth MCP Server`
   - Identifier: e.g. `https://your-server.example.com/mcp` (use your real MCP URL; this is your **Audience**)
   - Signing Algorithm: **RS256** → **Create**

3. **Create an Application** (for the MCP client):
   - **Applications** → **Applications** → **Create Application**
   - Name: e.g. `MCP Client`
   - Type: **Machine to Machine** (or **Native** for local clients)
   - Choose your API and authorize it; grant scopes: `openid`, `profile`, `email`
   - Note the **Client ID** and **Client Secret** if you need them for the client

4. **Note your Auth0 domain** (e.g. `your-tenant.auth0.com`) from the Auth0 Dashboard.

5. **Environment variables** (see step 5 below): you will set:
   - `AUTH0_DOMAIN` = your tenant domain (e.g. `your-tenant.auth0.com`)
   - `AUTH0_AUDIENCE` = the API Identifier you set (e.g. `https://your-server.example.com/mcp`)
   - `RESOURCE_SERVER_URL` = same as audience, or the public URL where your MCP server is reached (e.g. `https://your-server.example.com/mcp`)

### 3. Google Cloud setup (optional, for Gmail tools)

Only needed if you want `list_my_recent_emails` and `link_my_gmail`.

1. **Create or select a project** in [Google Cloud Console](https://console.cloud.google.com/).

2. **Enable Gmail API**:
   - **APIs & Services** → **Library** → search **Gmail API** → **Enable**.

3. **Configure OAuth consent screen**:
   - **APIs & Services** → **OAuth consent screen**.
   - User type: **External** → **Create**.
   - **App information**: name (e.g. `dibya-mcp-gmail`), support email, developer contact → **Save and Continue**.
   - **Scopes** → **Add or Remove Scopes** → add `https://www.googleapis.com/auth/gmail.readonly` → **Save and Continue**.
   - **Test users** (if in Testing mode): add the Gmail addresses that will use the app (e.g. your own) → **Save and Continue**.
   - **Summary** → **Back to Dashboard**.

4. **Create OAuth 2.0 credentials**:
   - **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
   - Application type: **Desktop app** (or **Web application** with redirect URI below).
   - Name: e.g. `MCP Gmail`.
   - If **Web application**: under **Authorized redirect URIs** add exactly: `http://localhost:8080/`.
   - **Create** → copy **Client ID** and **Client Secret**.

5. **Environment variables** (see step 5): you will set:
   - `GOOGLE_CLIENT_ID` = OAuth client Client ID
   - `GOOGLE_CLIENT_SECRET` = OAuth client Client Secret

### 4. Get a Gmail refresh token (optional, for Gmail tools)

The MCP server needs a **refresh token** issued by **your** OAuth client (tokens from Google OAuth Playground will not work).

1. **Add redirect URI in Google Cloud** (if not already):
   - **APIs & Services** → **Credentials** → your OAuth 2.0 Client ID.
   - Under **Authorized redirect URIs** add: `http://localhost:8080/` (with trailing slash) → **Save**.

2. **Run the one-time script** from the project root:
   ```bash
   uv run python scripts/get_gmail_refresh_token.py
   ```
   - The script prints the exact redirect URI to add if needed.
   - Press Enter to open the browser; sign in with the Google account whose Gmail you want to use.
   - After consent, the script prints a **refresh token**. Copy it.

3. **Link Gmail in the MCP server** (after the server is running and you are authenticated with Auth0):
   - Call the MCP tool **`link_my_gmail`** with that refresh token. The server stores it for your Auth0 user so **`list_my_recent_emails`** can work.

### 5. Environment variables

In the project root, create a `.env` file (see `.env.example`):

**Required (Auth0):**

```bash
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://your-server.example.com/mcp
RESOURCE_SERVER_URL=https://your-server.example.com/mcp
```

**Optional (Gmail):**

```bash
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
```

Optional: `GMAIL_TOKEN_STORE_PATH=.gmail_tokens.json` (default; where per-user refresh tokens are stored).

### 6. Run the server

```bash
uv run python main.py
```

Server runs at **http://0.0.0.0:8000/mcp** (or the URL you use in production, e.g. behind a reverse proxy). MCP clients must send requests with a valid Auth0 access token (Bearer) for your API.

---

## MCP tools

| Tool | Description |
|------|-------------|
| `greet_user` | Greets the authenticated user by name. |
| `fetch_instructions(prompt_name)` | Returns writing templates: `write_blog_post`, `write_social_post`, `write_video_chapters`. |
| `link_my_gmail(refresh_token)` | Links Gmail for the current Auth0 user using a Google refresh token (one-time). |
| `list_my_recent_emails(max_results)` | Lists recent Gmail messages for the authenticated user (default 10, max 20). Requires Gmail linked first. |

---

## Troubleshooting

- **“Gmail is not configured”**  
  Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`, then use `link_my_gmail` with a refresh token from `scripts/get_gmail_refresh_token.py`.

- **“redirect_uri_mismatch”**  
  Add exactly `http://localhost:8080/` to your Google OAuth client’s **Authorized redirect URIs** and save.

- **“This app’s request is invalid” / “only developer-approved testers”**  
  OAuth app is in **Testing**. In **APIs & Services** → **OAuth consent screen** → **Test users**, add your Gmail address. Or **Publish app** (you’ll see an “unverified app” warning until verification is done).

- **“unauthorized_client” when listing emails**  
  The refresh token must be from **your** OAuth client. Get a new one with `uv run python scripts/get_gmail_refresh_token.py` and call `link_my_gmail` again.

---

## Tech stack

- **FastMCP** – MCP server
- **Auth0** – OAuth 2.0 for MCP authentication
- **Google APIs** – Gmail read-only for the linked user
- **uv** – Python dependency management
