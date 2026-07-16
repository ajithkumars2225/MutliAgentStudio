# User Manual: Multi-Agent Developer Studio

Welcome to the **Multi-Agent Developer Studio**! This guide provides a comprehensive, step-by-step manual on how to run, configure, and utilize the studio for full-stack software development.

---

## 🚀 Part 1: How to Run the Studio

Follow these steps to launch the local backend server and load the web dashboard:

1. **Open your terminal** (PowerShell or Command Prompt) on Windows.
2. **Navigate to the studio directory**:
   ```powershell
   cd "C:\PERSONAL DATA\2.POC\AGENTS"
   ```
3. **Activate the Python virtual environment**:
   ```powershell
   .venv\Scripts\activate
   ```
4. **Start the FastAPI server**:
   ```powershell
   python app.py
   ```
   *Expected output:*
   ```text
   Starting Multi-Agent Developer Studio Server on http://localhost:8000...
   INFO:     Started server process [14268]
   INFO:     Waiting for application startup.
   [Terminal] Persistent PowerShell session started in: C:\PERSONAL DATA\2.POC\Student Form
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```
5. **Open your browser** and navigate to: **`http://localhost:8000`**

---

## ⚙️ Part 2: Configuring LLM Models & Settings

Before starting any development, configure your preferred LLM engine:

1. On the top navigation header, click **⚙️ LLM Settings**.
2. **Select your LLM Provider** (e.g. *Gemini*, *Claude*, *OpenAI*, *Ollama*).
3. **Input details**:
   * **Model Name** (e.g. `gemini-2.5-flash` or `claude-3-5-sonnet-latest`).
   * **API Key** (e.g., your Gemini or Anthropic API Key).
   * **Base URL** (Required for Ollama local endpoints or custom OpenAI-compatible proxies).
   * **Iteration Limit**: Set the maximum autonomous reasoning loops the agent is allowed to execute (Default: `15`).
   * **Approval Mode**: Choose if you want the agent to stop and ask for your approval before making changes.
   * **Semantic Caching Toggle**: Check **Enable Semantic Caching** to save API tokens and speed up execution.
4. Click **💾 Save Configurations**. *(Saved directly to the secure local SQLite database).*

---

## 🧠 Part 3: Semantic Caching Guide (Token Optimization)

To reduce API usage and accelerate agent iteration loops, we built a hybrid **Semantic Caching** engine:

* **How it works**: When the agent wants to query the LLM, it first checks if the query prompt matches previous queries in the SQLite database.
* **Vector Embeddings (Online)**: If using Gemini, OpenAI, or Ollama, it retrieves the prompt's mathematical vector representation and scans the database for cosine matches of **`>= 0.90`** similarity.
* **TF-IDF Cosine Fallback (Offline)**: If using Claude or working offline without key limits, it falls back to a custom word frequency cosine comparison matching prompts at **`>= 0.70`** similarity.
* **Effect**: When a hit occurs, the agent prints `[Semantic Cache Hit]` in the console and loads the cached file edits/actions instantly. This saves you money on tokens and reduces execution times to less than **5 milliseconds**!

---

## 🛠️ Part 4: Step-by-Step Development Workflows

### 🆕 Workflow A: Starting a New Project from Scratch
Use this workflow when you want the agents to build a new application inside an empty folder.

1. **Create an empty folder** on your Windows disk (e.g. `C:\PERSONAL DATA\2.POC\NewApp`).
2. In the Studio Files Explorer, click the **📂 Open Repository Folder** icon button.
3. Select your newly created empty folder `NewApp` in the native Windows folder selector dialog box.
4. In the prompt input block, type your design specifications:
   > *Example:* `"Create a FastAPI backend with SQLite database to store user contacts. Build an HTML frontend with tables and forms to create and read contacts. Include validation checks and python test scripts."`
5. Click **🚀 Run Studio**.
6. **Specs Review**: The studio will compile the specifications and display an **Approval Checkpoint** modal. Review the business goals and click **✓ Approve & Proceed**.
7. **Simulation Loop**: The **Implement Engineer** will write the code, the **QA Tester** will run automated tests, and the **Deployment Agent** will spin up the server.
8. **Vibe Check**: When deployment completes, the studio slides you to the **🌐 Live Web Preview** tab where you can interact with your newly running app!

---

### 🐛 Workflow B: Fixing Issues in an Existing Project
Use this workflow when you have a bug or error in your code and want the agents to diagnose and fix it.

1. Click **📂 Open Repository Folder** and select your existing project folder.
2. In the prompt input block, describe the error or copy-paste the error message:
   > *Example:* `"The contact form submission fails with a 500 error when the email field is blank. Find the bug in the backend routing logic, fix it, and update tests to verify it allows optional emails."`
3. Click **🚀 Run Studio**.
4. The **Impact Analyzer** will index your codebase, find files relating to contact forms and validation (`app.py`), and outline the bug fix.
5. Click **✓ Approve & Proceed**.
6. The agent modifies the files, runs your test suites, and commits the fix to Git once tests pass.

---

### ➕ Workflow C: Refactoring Code & Adding Features
Use this workflow when you want to add new functions, pages, or databases to an existing working app.

1. Open your project folder using the **📂 Open Repository Folder** button.
2. In the prompt input block, describe the changes:
   > *Example:* `"Add evolutionary validation to our contacts database. We need to store contact phone numbers. Add a phone number input to the UI form, add phone validation to the backend, and update the SQLite schema DDL to include a phone column."`
3. Click **🚀 Run Studio** and approve the impact analysis.
4. The agents will:
   * Edit the database connection scripts to run alter-table statements.
   * Add inputs to the HTML page.
   * Update backend routes.
   * Run tests to verify existing features are not broken (regression checks).

---

## 💎 Part 5: Advanced Enterprise Features Guide

### 1. Split-Terminal Panel Layout
The terminal console is split into two independent tab views to keep your work clean:
* **🐚 Shell Session**: A fully interactive Windows PowerShell. You can type commands, run scripts, compile binaries, and execute git tasks directly.
  * *Line-Buffered Engine*: Type commands, use `Backspace` to delete characters locally, and press `Enter` to execute. Use `Ctrl+C` to cancel running CLI operations.
* **🤖 Agent Console**: A dedicated read-only xterm console window that streams agent background operations. Displays agent reasoning, compiler logs, and test suites execution. It colorizes code logs (Cyan for Orchestrators, Magenta for Agents, Red for failures, Green for successes).
* *Note*: The studio automatically switches focus to **🤖 Agent Console** when simulation starts. You can toggle back to **🐚 Shell Session** at any time.

### 2. Git & TFS Source Control Management
* **Task Branches**: Every simulation run automatically checks out a new task branch: `studio-task-{id}`.
* **Auto-Commits**: Every time the agent completes a successful code change and validation checks pass, it auto-commits changes locally with a descriptive message (e.g. `QA Validation Success - Iteration 2`).
* **Git Status Badge**: Displays the active branch name pill in the panel header.

### 3. Git Control Center Modal
Clicking on the blue Git Branch status pill opens the Git Version Control Center modal:
* **Active Branch & Repo Status**: Shows if your workspace is `Clean` or `Modified`.
* **Recent Commits History**: Displays a list of the last 5 commits, showing short hash IDs and commit descriptions.
* **Pending Local Changes**: Displays modified, added, or deleted files.
* **Active Code Diff**: Displays a color-coded code diff (green for additions `+` and red for deletions `-`) comparing your workspace to the repository base state.

### 4. Live Web Application Preview
The IDE panel is tabbed into:
* **📁 File Editor**: Browse, read, edit, and save files.
* **🌐 Live Web Preview**: A built-in web browser that runs your application.
  * *Auto-refresh*: It scans deployment logs for server ports (e.g. `http://localhost:3000`), loads them into the iframe, and refreshes the preview automatically upon successful builds.
  * *Controls*: Type custom URLs in the address bar, reload with `🔄`, or click `↗️` to open in a new browser window.

### 5. CI/CD Pipeline Generator
When deploying projects, the agent automatically creates configuration files for major pipeline engines inside the workspace:
* **`azure-pipelines.yml`**: Configured to run TFS / Azure DevOps build and test pipelines on every check-in.
* **`.github/workflows/ci.yml`**: Configured to trigger GitHub Actions builds and security tests.
