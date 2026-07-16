# TFS (Team Foundation Server) Source Control Configuration Guide

This guide explains how to connect your **TFS connection** and **Collection name** to the Multi-Agent Developer Studio.

TFS supports two distinct source control modes. Follow the section below that matches your TFS team project setup.

---

## Mode 1: TFS Git Repositories (Recommended & Native)
If your TFS Collection uses Git repositories (which is standard for modern TFS / Azure DevOps Server installations), the agent supports it natively without any extra installations.

### 📝 Step-by-Step Configuration:
1. **Initialize the local workspace**:
   Open the Developer Studio, set your active workspace to your project folder, and click **Run Studio**. The agent will automatically initialize a local Git repository.
2. **Add your TFS remote connection**:
   Open your Windows command prompt inside the active project workspace folder, and link it to your TFS Collection URL:
   ```powershell
   # Syntax:
   # git remote add origin http://<tfs-server-name>:8080/tfs/<collection-name>/<project-name>/_git/<repo-name>
   
   # Example:
   git remote add origin http://tfs-server:8080/tfs/DefaultCollection/StudentProject/_git/StudentRepo
   ```
3. **Commit and Push**:
   When the agent finishes compiling and commits your changes locally, push the branch to TFS Git:
   ```powershell
   # Push the task branch to TFS
   git push origin studio-task-<history_id>
   ```

---

## Mode 2: TFS TFVC (Team Foundation Version Control)
If your TFS collection uses TFVC (path-based version control with `$//` paths), you can bridge it to the agent's Git operations using **`git-tfs`**.

`git-tfs` is a two-way bridge that lets you run local Git commands (which the agent uses) and check them directly into TFS as changesets/shelvesets.

### 📝 Step-by-Step Configuration:
1. **Install `git-tfs`**:
   Install `git-tfs` on your Windows machine using Chocolatey:
   ```powershell
   choco install git-tfs
   ```
   *(Ensure the `git-tfs` folder is in your Windows PATH environment variable).*
2. **Initialize or Clone from TFVC**:
   Instead of opening an empty folder, clone your TFVC workspace path using `git-tfs`:
   ```powershell
   # Syntax:
   # git tfs clone http://<tfs-server>:<port>/tfs/<collection-name> $/<project-path> <local-folder-name>
   
   # Example:
   git tfs clone http://tfs-server:8080/tfs/DefaultCollection $/StudentProject/Main C:\Projects\StudentForm
   ```
3. **Open in Developer Studio**:
   Open the Developer Studio, click the **📂 Open Repository Folder** icon, and select the cloned folder `C:\Projects\StudentForm`.
4. **Agent Operations**:
   The agent will run task-branch checkouts and auto-commits inside this folder using local Git commands.
5. **Check-in to TFS**:
   Once the agent finishes work, open your Windows command prompt in the folder and check the Git changes directly into TFS TFVC:
   ```powershell
   # Launch the TFS Check-in GUI Dialog to review and check in changes:
   git tfs checkin
   
   # Alternatively, check-in directly via command line:
   git tfs checkintool
   ```

---

## Credentials & Authentication:
When pushing or checking in to TFS, standard Windows NTLM or Personal Access Tokens (PAT) are used. 
* **If prompted for credentials**, type your TFS Windows domain username (e.g. `DOMAIN\username`) and your domain password.
* **If using Personal Access Tokens**, generate a PAT from your TFS user profile page and use it as your password.
