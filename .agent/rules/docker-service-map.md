---
trigger: always_on
---

# Role
Act as a Principal DevOps Engineer and Antigravity Environment Specialist.

# Objective
Establish a **Docker-First Command Execution Protocol** for this project.
The agent must strictly execute development commands (like `npm`, `python`, `pip`, `alembic`) inside the appropriate Docker containers defined in `docker-compose.yml`, rather than on the local host machine.

# Context Analysis
1.  **Analyze Infrastructure**: Read `docker-compose.yml` to identify the service names and their roles.
    -   Identify the service responsible for Frontend (likely running Node/Next.js).
    -   Identify the service responsible for Backend API (likely running Python/FastAPI).
    -   Identify the service for the Database (PostgreSQL).
2.  **Determine Mappings**: Create a mental map of tool-to-container relationships.
    -   Example: `npm` -> `frontend` container.
    -   Example: `python`, `pip`, `alembic` -> `backend_api` container.

# Phased Execution Plan

## Phase 1: Rule Definition (Planning)
Draft a section for `AGENTS.md` titled "## 🐳 Docker Execution Rules".
This section must define the following **Command Translation Logic**:
-   **Frontend Commands**: "When asked to run `npm install`, `npm run dev`, or `npx`, execute via `docker-compose exec [FRONTEND_SERVICE_NAME] [COMMAND]`."
-   **Backend Commands**: "When asked to run `python`, `pip install`, or `alembic`, execute via `docker-compose exec [BACKEND_SERVICE_NAME] [COMMAND]`."
-   **Database Commands**: "For SQL or DB checks, prefer using the `postgres` container."

**STOP and ask the user to confirm the service mappings are correct (e.g., is the backend service named `backend_api` or `api`?).**

## Phase 2: Implementation (Write AGENTS.md)
1.  **Create/Update `AGENTS.md`**: Append the approved "Docker Execution Rules" to the `AGENTS.md` file at the root of the repository.
2.  **Formatting**: Use clear Blockquotes or specific instruction steps to ensure the agent parses this with high priority.
3.  **Constraint**: Add a rule explicitly stating: "DO NOT run `npm` or `python` directly on the host shell unless explicitly instructed with 'run locally'."

## Phase 3: Verification
1.  **Test the Rule**: In the chat, simulate a request.
    -   Task: "Show me the command you would run to install a new package `axios` for the frontend."
    -   Expected Output: The agent should propose `docker-compose exec frontend npm install axios` (NOT `npm install axios`).

# Constraints
-   The rules must be written in English in `AGENTS.md` for better LLM adherence.
-   Ensure the mappings are dynamic based on the actual `docker-compose.yml` content.