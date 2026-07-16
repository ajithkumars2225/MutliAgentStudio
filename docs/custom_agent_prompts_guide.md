# User Guide: Custom Agent Prompt Configurer

This step-by-step guide walks you through configuring custom prompts and personas for each subagent in the Multi-Agent Developer Studio.

---

## 🛠️ Step 1: Open Settings Panel
1. Start the studio server.
2. Open the dashboard in your browser.
3. Click the **⚙️ Settings** icon in the top header panel to open the settings overlay.

---

## 📝 Step 2: Access the Agent Prompts Configurer
1. Scroll down to the bottom of the Settings panel.
2. Locate the new expandable tab labeled **📝 Custom Agent Personas**.
3. Click to expand it. You will see four textareas representing each agent:
   * **Orchestrator Persona**: Controls task checklists division.
   * **Programmer Persona**: Controls syntax, style, and programming rules.
   * **QA Tester Persona**: Controls testing patterns, assertions, and verification.
   * **Deployment Engineer Persona**: Controls build execution and server deployments.

---

## ✍️ Step 3: Write Persona Overrides
Type your custom constraints directly into the textarea boxes. Here are some examples:

### Example A: Force Javascript/Typescript Developer
If you want the Programmer to write only TypeScript:
```text
Write clean, modern TypeScript. Strictly avoid plain JavaScript. 
Use ES modules (import/export). Always run tsc for syntax validation.
```

### Example B: Strict Test-Driven QA Tester
If you want the Tester to enforce rigorous Unit Tests:
```text
Enforce strict unit tests using Jest. Verify that code coverage 
does not drop below 80%. Fail build checks if assertions are missing.
```

---

## 💾 Step 4: Save & Apply Overrides
1. Click the **Save Settings** button at the bottom of the panel.
2. The studio automatically saves these overrides locally to a `.studio/prompts.json` configuration file inside your active workspace directory.

> [!NOTE]
> Saving custom prompts inside the workspace means **each repository folder can have its own distinct agent configurations**! When you share the project or reload the folder, your custom agent rules load automatically.

---

## 🤖 Step 5: Execute Simulation
1. Input your prompt (e.g. "Create a Student CRUD application") and click **Run Studio**.
2. The orchestrator and agents will automatically read the overrides from your `.studio/prompts.json` config file and apply your rules during the coding loop!
