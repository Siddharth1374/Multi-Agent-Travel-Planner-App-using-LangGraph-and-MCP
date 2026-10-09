#WE Build a Multi-Agent Travel Planning System using LangGraph + MCP

---

# Requirements

## APIs

- Groq API
- Tavily API
- AviationStack API
- OpenWeatherMap API

## Tools

- PostgreSQL: https:
- Tavily MCP Server:

---

# Step 1: Create Python Environment


    python -m venv langgraph_env3


Activate:


    langgraph_env3\Scripts\activate


---

# Step 2: Install Dependencies


    pip install langgraph langchain langchain-openai langchain-groq langchain-community langchain-tavily psycopg[binary] psycopg_pool python-dotenv tavily-python requests streamlit



    pip install -U "psycopg[binary,pool]" langgraph-checkpoint-postgres


---

# Step 3: Install PostgreSQL

Download PostgreSQL:

https://www.postgresql.org/download/


---

# Step 4: Create Database


    CREATE DATABASE langgraph_memory_demo;

# Step 5: Setup .env File

# Setup AviationStack MCP Server (Local MCP Server)

Repository:

https://github.com/Pradumnasaraf/aviationstack-mcp

Open PowerShell:

    E:

    cd E:\Multi_agent_system_with_MCP


Clone repository:


    git clone https://github.com/Pradumnasaraf/aviationstack-mcp.git

    cd aviationstack-mcp


## Install UV

Check:

    uv --version


Install:

    pip install uv


If installation fails:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"


## Create .env File

    AVIATION_STACK_API_KEY=your_api_key_here


## Install Dependencies

    uv sync


This will:

- Create `.venv`
- Install dependencies
- Install AviationStack MCP package

## Activate Environment

    .venv\Scripts\activate


## Start MCP Server

    uv run -m aviationstack_mcp mcp run


or


    python -m aviationstack_mcp mcp run


The server will remain running and wait for MCP requests.

## Stop Server

    CTRL + C

# Example Prompt

    Plan a complete 7 days London trip including flights, hotels and sightseeing under 2 lakhs.


---

# Features

- Multi-Agent Architecture using LangGraph
- PostgreSQL Memory
- Tavily Search Integration
- AviationStack MCP Integration
- Weather MCP Integration
- Streamlit Web App
- Real-Time Travel Planning
