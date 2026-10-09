import os
import sys
import asyncio
import logging

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# API keys


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

_required = {
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "AVIATIONSTACK_API_KEY": AVIATION_STACK_API_KEY,
    "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
}
_missing = [name for name, value in _required.items() if not value]
if _missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Set them in your .env file before starting the app."
    )

AVIATIONSTACK_PYTHON = os.getenv("AVIATIONSTACK_MCP_PYTHON", sys.executable)
WEATHER_PYTHON = os.getenv("WEATHER_MCP_PYTHON", sys.executable)
WEATHER_SCRIPT = os.getenv(
    "WEATHER_MCP_SCRIPT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_mcp.py"),
)

if not os.path.isfile(WEATHER_SCRIPT):
    raise RuntimeError(
        f"Weather MCP script not found at {WEATHER_SCRIPT}. Set "
        "WEATHER_MCP_SCRIPT in your .env to the correct path."
    )

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
        },
        "aviationstack": {
            "transport": "stdio",
            "command": AVIATIONSTACK_PYTHON,
            "args": ["-m", "aviationstack_mcp", "mcp", "run"],
            "env": {"AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY},
        },
        "weather": {
            "transport": "stdio",
            "command": WEATHER_PYTHON,
            "args": [WEATHER_SCRIPT],
            "env": {"OPENWEATHER_API_KEY": OPENWEATHER_API_KEY},
        },
    }
)


_tools_lock = asyncio.Lock()
_tools_cache: dict | None = None


async def _discover_tools() -> dict:
    global _tools_cache

    if _tools_cache is not None:
        return _tools_cache

    async with _tools_lock:
        # Re-check after acquiring the lock in case another coroutine
        # finished discovery while we were waiting.
        if _tools_cache is None:
            tools = await client.get_tools()
            logger.info("Discovered MCP tools: %s", [t.name for t in tools])
            _tools_cache = {t.name: t for t in tools}

    return _tools_cache


def _get_tool(tools: dict, name: str):
    tool = tools.get(name)
    if tool is None:
        raise RuntimeError(
            f"MCP tool '{name}' was not found. Available tools: "
            f"{sorted(tools.keys())}"
        )
    return tool



# Tavily


async def tavily_mcp_search(query: str):
    tools = await _discover_tools()
    tool = _get_tool(tools, "tavily_search")
    return await tool.ainvoke({"query": query})



# Aviationstack


async def aviation_mcp_call(tool_name: str, tool_args: dict | None = None):
    tools = await _discover_tools()
    tool = _get_tool(tools, tool_name)
    return await tool.ainvoke(tool_args or {})


async def get_airports():
    try:
        return await aviation_mcp_call("list_airports")
    except RuntimeError as exc:
        return f"Airport tool unavailable: {exc}"


async def get_airlines():
    try:
        return await aviation_mcp_call("list_airlines")
    except RuntimeError as exc:
        return f"Airline tool unavailable: {exc}"



# Weather


async def weather_mcp_search(city: str):
    tools = await _discover_tools()
    tool = _get_tool(tools, "get_current_weather")
    return await tool.ainvoke({"city": city})


async def forecast_mcp_search(city: str):
    tools = await _discover_tools()
    tool = _get_tool(tools, "get_forecast")
    return await tool.ainvoke({"city": city})



# Destination extractor


llm = ChatGroq(model="llama-3.3-70b-versatile")

DESTINATION_PROMPT = """
Extract only the destination city or country.

Query:
{query}

Return only the destination name.
"""


def extract_destination(query: str) -> str:
    response = llm.invoke(DESTINATION_PROMPT.format(query=query))
    return response.content.strip()


async def extract_destination_async(query: str) -> str:
    response = await llm.ainvoke(DESTINATION_PROMPT.format(query=query))
    return response.content.strip()



# Manual smoke test: `python mcp_client.py`


async def _debug_main():
    await _discover_tools()
    result = await tavily_mcp_search("Best hotels in Delhi")
    print(result)


if __name__ == "__main__":
    asyncio.run(_debug_main())