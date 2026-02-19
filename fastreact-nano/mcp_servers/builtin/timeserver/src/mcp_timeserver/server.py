import datetime
import zoneinfo
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

server = Server("MCP-timeserver")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl(f"datetime://{timezone}/now"),
            name=f"Current time in {timezone}",
            description=f"The current time in {timezone}, as reported by the system clock",
            mimeType="text/plain",
        )
        for timezone in zoneinfo.available_timezones()
    ]


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    if uri.scheme == "datetime":
        assert uri.host is not None
        assert uri.path is not None

        resource = uri.unicode_string()
        time = resource.split("/")[-1]

        if time == "now":
            tz = uri.unicode_string().removeprefix("datetime://").removesuffix("/now")
            dt = datetime.datetime.now(zoneinfo.ZoneInfo(tz))
        else:
            # TODO: perhaps we should use templates to allow the client to use time values other then "now"
            raise ValueError(f"Unsupported time: {time}")

        return f"YYYY-MM-DD HH:MM:SS {dt.strftime("%Y-%m-%d %H:%M:%S")}"

    raise ValueError(f"Unsupported URI scheme: {uri.scheme}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-current-time",
            description="Get the current time in the configured local timezone",
            inputSchema={"type": "object"},
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name == "get-current-time":
        return [
            types.TextContent(
                type="text",
                text=f"The current time is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            )
        ]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="MCP-timeserver",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
