import asyncio
import json
import os
import sys
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Initialize Groq SDK (Free API Key from https://console.groq.com)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL_NAME = "openai/gpt-oss-120b"


def convert_mcp_to_openai_tools(mcp_tools):
  """Converts MCP tools format to OpenAI/Groq function-calling schema."""
  tools = []
  for t in mcp_tools.tools:
    tools.append({
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.inputSchema,
        },
    })
  return tools


async def run_agent_step(
    agent_name: str,
    system_prompt: str,
    allowed_tools: list,
    user_prompt: str,
    session: ClientSession,
    all_mcp_tools,
):
  """Executes reasoning and tool-calling loop for one agent."""
  logs = []

  # Filter tools by permissions (Single-Writer Rule)
  agent_tools = [
      t for t in all_mcp_tools if t["function"]["name"] in allowed_tools
  ]

  logs.append(f"[{agent_name}] Starting agent...")

  messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
  ]

  # Base API parameters
  kwargs = {
      "model": MODEL_NAME,
  }
  if agent_tools:
    kwargs["tools"] = agent_tools
    kwargs["tool_choice"] = "auto"

  response = client.chat.completions.create(messages=messages, **kwargs)
  response_message = response.choices[0].message

  # Loop while the model decides to call tools
  while response_message.tool_calls:
    # 1. Append assistant's response containing tool_calls
    messages.append(response_message)

    for tool_call in response_message.tool_calls:
      tool_name = tool_call.function.name
      tool_args = json.loads(tool_call.function.arguments)
      tool_use_id = tool_call.id

      logs.append(
          f"[{agent_name}] Model decided to call tool '{tool_name}' with args:"
          f" {tool_args}"
      )

      # 2. Execute call on MCP Server
      mcp_result = await session.call_tool(tool_name, arguments=tool_args)
      result_text = mcp_result.content[0].text
      logs.append(f"[MCP Server Output -> {tool_name}]: {result_text}")

      # 3. Append tool result back into conversation history
      messages.append({
          "role": "tool",
          "tool_call_id": tool_use_id,
          "content": result_text,
      })

    # 4. Re-query model with UPDATED messages array
    response = client.chat.completions.create(messages=messages, **kwargs)
    response_message = response.choices[0].message

  final_text = response_message.content or "Action completed successfully."
  logs.append(f"[{agent_name}] Final output: {final_text}")

  return final_text, logs

async def run_multi_agent_system(user_query: str):
  """Two-agent pipeline connected to custom MCP server."""
  server_params = StdioServerParameters(
      command=sys.executable, args=["mcp_server.py"]
  )

  all_logs = []
  all_logs.append(f"=== Incoming Query: '{user_query}' ===")

  async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
      await session.initialize()

      # 1. Retrieve tools from MCP server
      mcp_tools_raw = await session.list_tools()
      mcp_tools = convert_mcp_to_openai_tools(mcp_tools_raw)

      # 2. AGENT A (Planner): Read-Only search and analysis
      system_a = (
          "You are Agent A (Planner). Analyze the user request and find"
          " relevant task records using search_tasks. YOU HAVE NO WRITE"
          " PERMISSIONS (cannot add or edit tasks)."
      )

      plan_output, logs_a = await run_agent_step(
          agent_name="Agent A (Planner)",
          system_prompt=system_a,
          allowed_tools=["search_tasks"],
          user_prompt=user_query,
          session=session,
          all_mcp_tools=mcp_tools,
      )
      all_logs.extend(logs_a)

      # 3. HAND-OFF CONTRACT: Forward Agent A's output to Agent B
      all_logs.append(
          "--- [Hand-off] Context transferred from Agent A to Agent B ---"
      )

      # 4. AGENT B (Executor): Single Writer with rule validation
      system_b = (
          "You are Agent B (Executor Guardrail). You receive the plan from"
          " Agent A and perform database updates. Verify rules (priority must"
          " be 1 to 10) and execute add_task or update_task. If an error is"
          " returned, read the hint and retry with corrected inputs."
      )
      prompt_for_b = (
          f"Original User Request: '{user_query}'\nPlan and context from Agent"
          f" A:\n{plan_output}"
      )

      exec_output, logs_b = await run_agent_step(
          agent_name="Agent B (Executor)",
          system_prompt=system_b,
          allowed_tools=["add_task", "update_task"],
          user_prompt=prompt_for_b,
          session=session,
          all_mcp_tools=mcp_tools,
      )
      all_logs.extend(logs_b)

      return all_logs


if __name__ == "__main__":
  query = "Add task 'Prepare demo' with priority 12"
  logs = asyncio.run(run_multi_agent_system(query))
  for line in logs:
    print(line)