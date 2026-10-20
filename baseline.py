import json


def run_single_agent_baseline(query: str, mcp_client_call_fn) -> dict:
  """Single agent baseline: has access to search_tasks, add_task, update_task[cite: 89]."""
  # Simulated reasoning loop for single agent
  logs = [f"[Baseline Agent] Received query: '{query}'"]

  if "show" in query.lower() or "find" in query.lower():
    res = mcp_client_call_fn("search_tasks", {"category": "Study"})
    logs.append(f"[Baseline Agent] Executed tool 'search_tasks' -> {res}")
    return {"status": "success", "logs": logs, "result": res}

  elif "add" in query.lower():
    # Attempting direct write
    res = mcp_client_call_fn(
        "add_task",
        {"task_name": "New Task", "priority": 12, "category": "Study"},
    )
    logs.append(f"[Baseline Agent] Executed tool 'add_task' -> {res}")
    parsed = json.loads(res)

    if parsed.get("status") == "error":
      logs.append(
          f"[Baseline Agent] Hit Error: {parsed['message']}. Retrying..."
      )
      res = mcp_client_call_fn(
          "add_task",
          {"task_name": "New Task", "priority": 9, "category": "Study"},
      )
      logs.append(f"[Baseline Agent] Retried 'add_task' -> {res}")

    return {"status": "success", "logs": logs, "result": res}

  else:
    res = mcp_client_call_fn(
        "update_task", {"task_id": "T-999", "new_state": "done"}
    )
    logs.append(f"[Baseline Agent] Direct call 'update_task' -> {res}")
    return {"status": "error_unrecovered", "logs": logs, "result": res}