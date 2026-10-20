# Multi-Agent Task Planner (MCP Architecture)

Двоагентна автономна система для управління завданнями на базі **Model Context Protocol (MCP)** та **Groq Cloud API** (`openai/gpt-oss-120b`). проєкт демонструє розділення ролей (**Planner vs Executor**) та використання **Single-Writer Guardrail** для безпечної роботи з даними.

---

## Структура проєкту

```text
.
├── harness.py          # MCP Client Runner, Agent Loop, Guardrails & Hand-off Contract
├── mcp_server.py      # MCP Server з бізнес-логікою та інструментами (Tools)
├── eval.py            # Набір автотестів для порівняння 1-Agent vs 2-Agent
├── storage/
│   └── tasks.csv      # База даних завдань (CSV Storage)
├── requirements.txt   # Залежності проєкту
└── README.md          # Документація проєкту

## Tool cхема
`search_tasks` (Read-Only) — Пошук та вичитання завдань з tasks.csv. Доступний тільки для Agent A (Planner).

`add_task` (Write State) — Валідація та створення нового завдання з генерацією ID. Доступний тільки для Agent B (Executor).

`update_task` (Mutate) — Зміна стану або параметрів існуючого завдання за його ID. Доступний тільки для Agent B (Executor).