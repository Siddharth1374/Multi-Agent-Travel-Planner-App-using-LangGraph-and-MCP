# WE LangGraph Multi-Agent Travel Booking System with Long-Term Memory

import os
import uuid
import asyncio
from typing import TypedDict, Annotated
import operator

import psycopg
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq

from mcp_client import (
    tavily_mcp_search,
    aviation_mcp_call,
    extract_destination_async,
    forecast_mcp_search,
    weather_mcp_search,
)

load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")

llm = ChatGroq(model="llama-3.3-70b-versatile")



# State


class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int
    weather_results: str


FLIGHT_AGENT_PROMPT = """
You are a travel flight expert.

User Query:
{query}

Airport Information:
{airport_data}

Airline Information:
{airline_data}

Generate:

1. Likely departure airport
2. Likely arrival airport
3. Airlines serving this route
4. Typical flight duration
5. Estimated airfare range
6. Peak season pricing warning
7. Booking advice

Return concise travel guidance.
"""


async def flight_agent(state: TravelState):
    print("\nINSIDE FLIGHT AGENT\n")
    query = state["user_query"]

    try:
        airports = await aviation_mcp_call("list_airports")
        airlines = await aviation_mcp_call("list_airlines")

        prompt = FLIGHT_AGENT_PROMPT.format(
            query=query,
            airport_data=str(airports)[:3000],
            airline_data=str(airlines)[:3000],
        )

        response = await llm.ainvoke(
            [
                SystemMessage(content="You are an expert travel flight planner."),
                HumanMessage(content=prompt),
            ]
        )
        flight_data = response.content

    except Exception as exc:
        flight_data = f"Flight information unavailable: {exc}"

    return {
        "flight_results": flight_data,
        "messages": [AIMessage(content="Flight recommendations generated")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


async def hotel_agent(state: TravelState):
    query = f"Best hotels for {state['user_query']}"

    try:
        hotel_results = await tavily_mcp_search(query)
    except Exception as exc:
        hotel_results = f"Hotel information unavailable: {exc}"

    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel information fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


async def weather_agent(state: TravelState):
    try:
        city = await extract_destination_async(state["user_query"])
        weather_data = await weather_mcp_search(city)
        forecast_data = await forecast_mcp_search(city)
        weather_results = f"""
        Current Weather:
        {weather_data}

        Forecast:
        {forecast_data}
        """
    except Exception as exc:
        weather_results = f"Weather information unavailable: {exc}"

    return {
        "weather_results": weather_results,
        "messages": [AIMessage(content="Weather information fetched")],
        # extract_destination_async makes an LLM call, so count it here too
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


async def itinerary_agent(state: TravelState):
    prompt = f"""
    Create a travel itinerary.
    User Query:
    {state['user_query']}

    Flight Results:
    {state['flight_results']}

    Hotel Results:
    {state['hotel_results']}

    Weather Information:
    {state['weather_results']}
    """

    response = await llm.ainvoke(
        [
            SystemMessage(content="You are an expert travel planner"),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }



# Graph


graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("itinerary_agent", itinerary_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "weather_agent")
graph.add_edge("weather_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", END)

# Persistent connection so both CLI and Streamlit can share the compiled app
_conn = psycopg.connect(DATABASE_URL)
checkpointer = PostgresSaver(_conn)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)


async def run_travel_request(user_input: str, thread_id: str | None = None) -> dict:
    """Invoke the graph once for a single travel request."""
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}

    return await app.ainvoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "weather_results": "",
            "llm_calls": 0,
        },
        config=config,
    )


async def _cli_main():
    user_input = input("Enter travel request: ")
    result = await run_travel_request(user_input)

    print("\nFINAL RESPONSE:\n")
    for msg in result["messages"]:
        print(msg.content)


if __name__ == "__main__":
    # Every run starts fresh (new thread_id each time).
    asyncio.run(_cli_main())