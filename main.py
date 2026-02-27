import re
import os

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.provider import AccessToken
from pydantic import AnyHttpUrl
from dotenv import load_dotenv

from utils.auth import create_auth0_verifier

# Load environment variables from .env file
load_dotenv()

# Get Auth0 configuration from environment
auth0_domain = os.getenv("AUTH0_DOMAIN")
resource_server_url = os.getenv("RESOURCE_SERVER_URL")

if not auth0_domain:
    raise ValueError("AUTH0_DOMAIN environment variable is required")
if not resource_server_url:
    raise ValueError("RESOURCE_SERVER_URL environment variable is required")

# Load server instructions
with open("prompts/server_instructions.md", "r") as file:
    server_instructions = file.read()

# Initialize Auth0 token verifier
token_verifier = create_auth0_verifier()

# Create an MCP server with OAuth authentication
mcp = FastMCP(
    "yt-mcp",
    instructions=server_instructions,
    host="0.0.0.0",
    # OAuth Configuration
    token_verifier=token_verifier,  
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(f"https://{auth0_domain}/"),
        resource_server_url=AnyHttpUrl(resource_server_url),
        required_scopes=["openid", "profile", "email"],
    ),
)

@mcp.tool()
def fetch_instructions(prompt_name: str,context: Context) -> str:
    """
    Fetch instructions for a given prompt name from the prompts/ directory

    Args:
        prompt_name (str): Name of the prompt to fetch instructions for
        Available prompts: 
            - write_blog_post
            - write_social_post
            - write_video_chapters

    Returns:
        str: Instructions for the given prompt
    """
    request_object = context.request_context.request
    headers: dict[str, str] = request_object.headers
    '''accesstoken: AccessToken =  token_verifier.verify_token(headers.get("authorization"))'''
    script_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(script_dir, "prompts", f"{prompt_name}.md")
    with open(prompt_path, "r") as f:
        return f.read()
    
@mcp.tool("greet_user", description="Greets the authenticated user.")
def greet_user(context: Context):
    request_object = context.request_context.request
    headers: dict[str, str] = request_object.headers
    accestoken = headers.get("authorization")
    user_info = token_verifier.get_userinfo(accestoken)
    print(f"User Info: {user_info}")
    return 'Hello, ' + user_info.name + '! Welcome to the MCP server.'

if __name__ == "__main__":
    mcp.run(transport='streamable-http')