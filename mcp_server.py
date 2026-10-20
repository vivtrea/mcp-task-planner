import csv
import json
import os
from typing import Optional
from mcp.server.fastmcp import FastMCP

CSV_FILE = os.path.join(
    os.path.dirname(__file__), "storage", "tasks.csv"
)

mcp = FastMCP("TaskManager")


def _read_csv():
  if not os.path.exists(CSV_FILE):
    return []
  with open(CSV_FILE, mode="r", encoding="utf-8") as f:
    return list(csv.DictReader(f))


def _write_csv(rows):
  fieldnames = [
      "task_id",
      "task_name",
      "priority",
      "category",
      "state",
      "due_date",
  ]
  with open(CSV_FILE, mode="w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


@mcp.tool()
def search_tasks(
    category: Optional[str] = None,
    min_priority: Optional[int] = None,
    state: Optional[str] = None,
) -> str:
  """Search and filter tasks from tasks.csv (READ-ONLY)."""
  rows = _read_csv()
  filtered = []

  for r in rows:
    if category and r["category"].lower() != category.lower():
      continue
    if min_priority and int(r["priority"]) < min_priority:
      continue
    if state and r["state"].lower() != state.lower():
      continue
    filtered.append(r)

  filtered.sort(key=lambda x: int(x["priority"]), reverse=True)
  return json.dumps(
      {"count": len(filtered), "tasks": filtered}, ensure_ascii=False
  )


@mcp.tool()
def add_task(
    task_name: str,
    priority: int,
    category: str,
    due_date: str,
) -> str:
  """Appends a new task row to tasks.csv (STATE-CHANGING)."""
  # Rule validation: priority 1..10
  if priority < 1 or priority > 10:
    return json.dumps({
        "status": "error",
        "error_code": "invalid_priority",
        "message": (
            f"Priority must be an integer between 1 and 10 (got {priority})."
        ),
        "hint": "Retry with a valid priority integer from 1 to 10.",
        "retryable": True,
    })

  rows = _read_csv()
  new_id = f"T-{101 + len(rows)}"
  new_row = {
      "task_id": new_id,
      "task_name": task_name,
      "priority": str(priority),
      "category": category,
      "state": "yet to be started",
      "due_date": due_date,
  }
  rows.append(new_row)
  _write_csv(rows)

  return json.dumps(
      {"status": "success", "task_id": new_id, "row": new_row},
      ensure_ascii=False,
  )


@mcp.tool()
def update_task(
    task_id: str,
    new_state: Optional[str] = None,
    new_priority: Optional[int] = None,
) -> str:
  """Updates state or priority for an existing task_id (STATE-CHANGING)."""
  rows = _read_csv()
  target = None

  for r in rows:
    if r["task_id"].upper() == task_id.upper():
      target = r
      break

  if not target:
    return json.dumps({
        "status": "error",
        "error_code": "task_not_found",
        "message": f"Task '{task_id}' was not found in database.",
        "hint": "Ask Agent A to run search_tasks to verify active task IDs.",
        "retryable": True,
    })

  if new_priority is not None:
    if new_priority < 1 or new_priority > 10:
      return json.dumps({
          "status": "error",
          "error_code": "invalid_priority",
          "message": f"Priority must be 1 to 10 (got {new_priority}).",
          "hint": "Provide a priority between 1 and 10.",
          "retryable": True,
      })
    target["priority"] = str(new_priority)

  if new_state:
    valid_states = ["yet to be started", "in process", "done"]
    if new_state.lower() not in valid_states:
      return json.dumps({
          "status": "error",
          "error_code": "invalid_state",
          "message": f"Invalid state '{new_state}'. Must be one of {valid_states}.",
          "hint": f"Retry with one of: {valid_states}",
          "retryable": True,
      })
    target["state"] = new_state.lower()

  _write_csv(rows)
  return json.dumps(
      {"status": "success", "updated_task": target}, ensure_ascii=False
  )


if __name__ == "__main__":
  mcp.run()