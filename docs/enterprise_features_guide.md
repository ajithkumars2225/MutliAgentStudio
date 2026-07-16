# Documentation & Guide: Git/TFS, Live Preview, and CI/CD features

This guide provides step-by-step instructions on how to use and verify the three newly added enterprise features inside the Multi-Agent Developer Studio.

---

## Feature 1: Git & TFS Git Version Control

This feature automates local backup, change tracking, and task-specific isolation so you never lose working code.

### 💡 How It Works under the Hood
1. **Branch Isolation**: When you click **Run Studio**, the backend checks if the folder is a Git repository. If not, it runs `git init` locally.
2. **Task Branches**: It checks out a branch matching the studio run ID: `studio-task-{history_id}`. This isolates the agent's work from your default `main` or `master` branch.
3. **Local Credentials**: It sets up local Git configurations (`Agent Studio <agent@developer.studio>`) so that commits work immediately even if Git is not globally configured.
4. **Auto-Commits**: Upon successful testing and validation, a local git commit is created (e.g., `QA Validation Success - Iteration 1`).

### 📝 Step-by-Step Guide to Use:
1. Open the studio dashboard at `http://localhost:8000`.
2. Look at the top of the **Generated Workspace** panel. You will see a blue badge with a branch icon: `🌿 studio-task-{id}`.
3. As the agent is working and successfully completing iteration loops:
   * View the modified files list by typing `git status` in your local terminal.
   * View recent commits created by the agent by running:
     ```powershell
     git log --oneline
     ```
4. **To push changes to your Git/TFS account**:
   Once the agent finishes compiling your app, open your Windows command prompt in the project workspace and run:
   ```powershell
   # Add your remote Git/TFS URL (if not already set)
   git remote add origin <your-github-or-tfs-git-repo-url>
   
   # Push your task branch to the cloud
   git push origin studio-task-<id>
   ```

---

## Feature 2: Live Web Application Preview

This feature lets you interact with and test the visual interface of running web applications directly on the studio dashboard.

### 💡 How It Works under the Hood
1. **Log Detection**: When the **Deployment Agent** starts your web server, the studio parses the terminal output in real-time looking for URLs like `http://localhost:3000` or `http://127.0.0.1:8080`.
2. **Piped Stream**: The active URL is passed back to the frontend status poll.
3. **Auto-Reload**: When the runner finishes, the preview pane refreshes its internal browser frame (`<iframe>`) and displays the page.

### 📝 Step-by-Step Guide to Use:
1. Enter a requirements prompt that develops a web app (e.g. *“Create a student CRUD form page and run a local server”*).
2. Click **Run Studio**.
3. Once the deployment finishes successfully:
   * The studio will automatically switch from the **📁 File Editor** tab to the **🌐 Live Web Preview** tab.
   * The web application will load directly inside the built-in browser panel.
4. **Interacting with the Preview**:
   * Click buttons, type in input fields, and perform CRUD operations directly inside the preview pane.
   * If you want to force a refresh of the page, click the **`🔄 Reload`** button next to the address bar.
   * To open the web app in a standard browser tab, click the **`↗️ Open Tab`** button.
   * If the server is running on a different port that wasn't auto-detected, simply type the URL (e.g. `http://localhost:5000`) into the address bar input and press **Enter**.

---

## Feature 3: CI/CD Pipeline Auto-Generator

This feature writes the pipeline files required to automatically test and audit your code whenever you push it to GitHub or Azure DevOps/TFS.

### 💡 How It Works under the Hood
During the deployment phase, the agent writes pipeline configuration files matching modern DevOps providers:
* **`azure-pipelines.yml`** for Azure DevOps/TFS.
* **`.github/workflows/ci.yml`** for GitHub.

### 📝 Step-by-Step Guide to Use:
1. Inspect the workspace file tree after a successful deployment. You will see:
   * A file named `azure-pipelines.yml` in the root folder.
   * A folder named `.github/workflows/` containing a `ci.yml` file.
2. Open the files to review their configurations. You will see tasks configured to:
   * Install runtime packages (`npm install`, `pip install`, etc.).
   * Run syntax compilation audits.
   * Run your project's unit tests (`npm test`, `pytest`).
   * Trigger static code security vulnerability scans.

### 🛠️ Setting up the Pipelines:
* **For GitHub Actions**:
  1. Push the generated code to your GitHub repository.
  2. Click on the **Actions** tab on your GitHub repository page.
  3. GitHub will automatically detect the `.github/workflows/ci.yml` file and start executing the build pipeline on every commit!
* **For Azure DevOps / TFS**:
  1. Push the branch to Azure Repos/TFS.
  2. Navigate to Azure DevOps $\rightarrow$ **Pipelines**.
  3. Click **New Pipeline**, select your Git/TFS repository, and point it to the existing `azure-pipelines.yml` file in your project.
  4. Save and run the pipeline!
