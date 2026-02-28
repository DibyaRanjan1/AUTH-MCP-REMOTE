import os

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl
from dotenv import load_dotenv

from utils.auth import create_auth0_verifier
from utils.gmail import (
    is_gmail_configured,
    list_recent_emails,
    store_refresh_token,
)

# Load environment variables from .env file
load_dotenv()

# Get Auth0 configuration from environment
auth0_domain = os.getenv("AUTH0_DOMAIN")
resource_server_url = os.getenv("RESOURCE_SERVER_URL")

if not auth0_domain:
    raise ValueError("AUTH0_DOMAIN environment variable is required")
if not resource_server_url:
    raise ValueError("RESOURCE_SERVER_URL environment variable is required")

# Server instructions for MCP clients
SERVER_INSTRUCTIONS = """# Auth MCP Server

This server provides tools with OAuth authentication (Auth0) and optional Gmail access for the logged-in user.

## Available Tools

### greet_user
Greets the authenticated user by name.

### fetch_instructions
Retrieves specialized writing instruction templates.

**Parameters:**
- `prompt_name` (string): One of `write_blog_post`, `write_social_post`, `write_video_chapters`

**Returns:** Instructions for the requested content type.

### link_my_gmail
Links the authenticated user's Gmail account to this server. Call once with a Google OAuth refresh token (e.g. from get_gmail_refresh_token script).

**Parameters:**
- `refresh_token` (string): Google OAuth refresh token

### list_my_recent_emails
Lists the most recent emails from the authenticated user's Gmail inbox. Requires Gmail to be linked first via `link_my_gmail`.

**Parameters:**
- `max_results` (int, optional): Number of emails to return (1–20, default 10)

**Returns:** Subject, from, date, and snippet for each message.
"""

# Initialize Auth0 token verifier
token_verifier = create_auth0_verifier()

# Create an MCP server with OAuth authentication
mcp = FastMCP(
    "yt-mcp",
    instructions=SERVER_INSTRUCTIONS,
    host="0.0.0.0",
    # OAuth Configuration
    token_verifier=token_verifier,  
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"https://{auth0_domain}/"),
        authorization_server_url=AnyHttpUrl(f"https://{auth0_domain}/"),
        resource_server_url=AnyHttpUrl(resource_server_url),
        required_scopes=["openid", "profile", "email"],
    ),
)

PROMPTS = {
    "write_blog_post": """
Write a detailed blog post with:
- Engaging introduction
- Clear headings
- Practical examples
- Strong conclusion
""",

    "write_social_post": """
Write a short, engaging social media post with:
- Hook
- Value
- CTA
""",

    "write_video_chapters": """
Generate YouTube video chapters with:
- Timestamp format
- Clear topic labels
"""
}

@mcp.tool()
def fetch_instructions(prompt_name: str, context: Context) -> str:
    if prompt_name not in PROMPTS:
        return f"Prompt '{prompt_name}' not found."

    return PROMPTS[prompt_name]
    
@mcp.tool("greet_user", description="Greets the authenticated user.")
def greet_user(context: Context) -> str:
    """Return a greeting for the authenticated user."""
    request_object = context.request_context.request
    headers: dict[str, str] = request_object.headers
    access_token = headers.get("authorization")
    if not access_token:
        return "Hello! You are not authenticated."
    user_info = token_verifier.get_userinfo(access_token)
    return f"Hello, {user_info.name}! Welcome to the MCP server."


def _get_auth0_sub(context: Context) -> str | None:
    """Extract Auth0 user id (sub) from the request. Returns None if not authenticated."""
    request_object = context.request_context.request
    auth_header = request_object.headers.get("authorization")
    if not auth_header:
        return None
    try:
        user_info = token_verifier.get_userinfo(auth_header)
        return user_info.sub
    except Exception:
        return None


@mcp.tool(
    "link_my_gmail",
    description="Link your Gmail account to this MCP server for the logged-in user. "
    "Provide the Google OAuth refresh token (e.g. from OAuth 2.0 Playground).",
)
def link_my_gmail(refresh_token: str, context: Context) -> str:
    """Store the user's Gmail refresh token so list_my_recent_emails can work."""
    if not is_gmail_configured():
        return (
            "Gmail is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env "
            "(see .env.example), then use link_my_gmail with a refresh token."
        )
    sub = _get_auth0_sub(context)
    if not sub:
        return "You must be authenticated (Auth0) to link Gmail."
    store_refresh_token(sub, refresh_token.strip())
    return "Gmail linked successfully. You can now use list_my_recent_emails."


@mcp.tool(
    "list_my_recent_emails",
    description="List the most recent emails from the authenticated user's Gmail inbox.",
)
def list_my_recent_emails(max_results: int = 10, context: Context | None = None) -> str:
    """Return a summary of the user's latest Gmail messages."""
    if context is None:
        return "Not available: no request context."
    if not is_gmail_configured():
        return (
            "Gmail is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env "
            "(see .env.example). Then use link_my_gmail with a refresh token from "
            "https://developers.google.com/oauthplayground (scope: gmail.readonly)."
        )
    sub = _get_auth0_sub(context)
    if not sub:
        return "You must be authenticated (Auth0) to list emails."
    max_results = min(max(1, max_results), 20)
    emails = list_recent_emails(sub, max_results=max_results)
    if not emails:
        return (
            "No emails found. If you haven't linked Gmail yet, use link_my_gmail with your "
            "Google OAuth refresh token (e.g. from https://developers.google.com/oauthplayground)."
        )
    lines = []
    for i, e in enumerate(emails, 1):
        snippet = (e.get("snippet") or "")[:120]
        if len(e.get("snippet") or "") > 120:
            snippet += "..."
        lines.append(
            f"{i}. [{e.get('subject', '(No subject)')}] From: {e.get('from', '')} | {e.get('date', '')}\n   {snippet}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport='streamable-http')