import sys
import asyncio
import traceback
from pathlib import Path

from mcp import Client, StdioServerParameters


class PostgreSQLMCPClient:

    def __init__(self):

        # Locate project root directory
        project_root = Path(__file__).resolve().parents[2]

        # Configure MCP server process
        self.server_parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "app.server.mcp_server",
            ],
            cwd=str(project_root),
        )

    # ==========================================
    # CREATE MCP CLIENT
    # ==========================================

    def create_client(self):

        return Client(self.server_parameters)

    # ==========================================
    # TEST MCP CONNECTION
    # ==========================================

    async def test_connection(self):

        client = self.create_client()

        try:
            print("\nConnecting to PostgreSQL MCP Server...")

            async with client:

                print("\nMCP CLIENT CONNECTED SUCCESSFULLY")

                # Discover available MCP tools
                tools_response = await client.list_tools()

                print("\nREGISTERED MCP TOOLS:")

                for tool in tools_response.tools:
                    print(f"  - {tool.name}")

                return True

        except Exception as error:

            print("\nMCP CLIENT CONNECTION FAILED")
            print(f"Error Type: {type(error).__name__}")
            print(f"Error Message: {error}")

            traceback.print_exc()

            return False


# ==============================================
# TEST CLIENT
# ==============================================

if __name__ == "__main__":

    client_manager = PostgreSQLMCPClient()

    asyncio.run(client_manager.test_connection())