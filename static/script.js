// GLOBAL STATES
let lastLogCount = 0;
let existingFiles = [];
let pollingInterval = null;
let currentActiveFile = null;
let currentActiveParentId = null;
let openFiles = {}; // filepath -> { content, isDirty, mode }
let codeEditor = null; // CodeMirror instance

// DOM ELEMENTS
const editorTabsBar = document.getElementById("editor-tabs-bar");
const providerSelect = document.getElementById("provider-select");
const geminiSettings = document.getElementById("gemini-settings");
const geminiModelInput = document.getElementById("gemini-model-input");
const iterationsSlider = document.getElementById("iterations-slider");
const iterationsVal = document.getElementById("iterations-val");
const promptInput = document.getElementById("prompt-input");
const startBtn = document.getElementById("start-btn");
const clearLogsBtn = document.getElementById("clear-logs-btn");
const consoleBox = document.getElementById("terminal-container");
const fileTree = document.getElementById("file-tree");
const activeFilename = document.getElementById("active-filename");

function updateActiveFilenameUI(filepath) {
    if (!activeFilename) return;
    
    if (!filepath || filepath === "Select a file from explorer") {
        activeFilename.innerHTML = `<span style="color: var(--text-secondary); font-style: italic;">Select a file from explorer</span>`;
        return;
    }
    
    const normalized = filepath.replace(/\\/g, "/");
    const parts = normalized.split("/");
    const filename = parts.pop();
    
    const ext = filename.split('.').pop().toLowerCase();
    let icon = "📄";
    if (ext === "py") icon = "🐍";
    else if (ext === "js" || ext === "json") icon = "🟨";
    else if (ext === "html" || ext === "cshtml") icon = "🌐";
    else if (ext === "css") icon = "🎨";
    else if (ext === "cs") icon = "⚙️";
    
    let breadcrumbHTML = "";
    if (parts.length > 0) {
        const folderPath = parts.join(" / ");
        breadcrumbHTML += `<span style="color: rgba(255, 255, 255, 0.35); font-family: monospace; font-size: 0.72rem; margin-right: 0.3rem;">${folderPath} /</span> `;
    }
    
    breadcrumbHTML += `
        <span style="
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(0, 223, 216, 0.08);
            border: 1px solid rgba(0, 223, 216, 0.25);
            padding: 0.15rem 0.6rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.75rem;
            color: var(--accent-cyan);
            font-weight: 500;
            box-shadow: 0 0 8px rgba(0, 223, 216, 0.05);
        ">
            <span>${icon}</span>
            <span>${filename}</span>
        </span>
    `;
    
    activeFilename.innerHTML = breadcrumbHTML;
}

const globalStatusDot = document.getElementById("global-status-dot");
const globalStatusText = document.getElementById("global-status-text");
const semanticCacheToggle = document.getElementById("semantic-cache-toggle");

// HITL MODAL ELEMENTS
const hitlModal = document.getElementById("hitl-modal");
const hitlStageTitle = document.getElementById("hitl-stage-title");
const hitlMarkdownContent = document.getElementById("hitl-markdown-content");
const hitlFeedbackInput = document.getElementById("hitl-feedback-input");
const hitlApproveBtn = document.getElementById("hitl-approve-btn");
const hitlRejectBtn = document.getElementById("hitl-reject-btn");
const copyCodeBtn = document.getElementById("copy-code-btn");
const saveCodeBtn = document.getElementById("save-code-btn");
const closeFileBtn = document.getElementById("close-file-btn");

// Initialize CodeMirror Editor for actual IDE coding feel
const editorContainer = document.getElementById("editor-container");
if (editorContainer) {
    codeEditor = CodeMirror(editorContainer, {
        value: "",
        mode: "python",
        theme: "dracula",
        lineNumbers: true,
        indentUnit: 4,
        matchBrackets: true,
        autoCloseBrackets: true,
        lineWrapping: true
    });
    
    codeEditor.on("change", () => {
        if (currentActiveFile && openFiles[currentActiveFile]) {
            const currentVal = codeEditor.getValue();
            if (currentVal !== openFiles[currentActiveFile].content) {
                openFiles[currentActiveFile].content = currentVal;
                if (!openFiles[currentActiveFile].isDirty) {
                    openFiles[currentActiveFile].isDirty = true;
                    renderTabs();
                }
            }
        }
    });
}

// EVENT LISTENERS

if (copyCodeBtn) {
    copyCodeBtn.addEventListener("click", () => {
        if (!codeEditor) return;
        const codeText = codeEditor.getValue();
        if (!codeText) return;
        
        navigator.clipboard.writeText(codeText).then(() => {
            const originalText = copyCodeBtn.textContent;
            copyCodeBtn.textContent = "✓ Copied!";
            setTimeout(() => {
                copyCodeBtn.textContent = originalText;
            }, 1500);
        }).catch(err => {
            console.error("Failed to copy code: ", err);
        });
    });
}

if (saveCodeBtn) {
    saveCodeBtn.addEventListener("click", () => {
        if (!currentActiveFile || !codeEditor) return;
        
        saveCodeBtn.disabled = true;
        const content = codeEditor.getValue();
        
        fetch("/api/file/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: currentActiveFile,
                content: content
            })
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail || "Failed to save file") });
            return r.json();
        })
        .then(() => {
            if (currentActiveFile && openFiles[currentActiveFile]) {
                openFiles[currentActiveFile].isDirty = false;
                renderTabs();
            }
            const originalText = saveCodeBtn.textContent;
            saveCodeBtn.textContent = "✓ Saved!";
            setTimeout(() => {
                saveCodeBtn.textContent = originalText;
                saveCodeBtn.disabled = false;
            }, 1200);
        })
        .catch(err => {
            alert(err.message);
            saveCodeBtn.disabled = false;
        });
    });
}

const modelInput = document.getElementById("model-input");
const modelLabel = document.getElementById("model-label");
const openrouterModelSelect = document.getElementById("openrouter-model-select");
const openrouterCustomModelInput = document.getElementById("openrouter-custom-model-input");
const apiKeyGroup = document.getElementById("api-key-group");
const apiKeyLabel = document.getElementById("api-key-label");
const apiKeyInput = document.getElementById("api-key-input");
const baseUrlGroup = document.getElementById("base-url-group");
const baseUrlLabel = document.getElementById("base-url-label");
const baseUrlInput = document.getElementById("base-url-input");
const approvalModeSelect = document.getElementById("approval-mode-select");
const retryBtn = document.getElementById("retry-btn");

let isAgentRunning = false;
let wasAgentRunning = false;
let runningPrompt = "";

if (openrouterModelSelect && openrouterCustomModelInput) {
    openrouterModelSelect.addEventListener("change", () => {
        if (openrouterModelSelect.value === "custom") {
            openrouterCustomModelInput.style.display = "block";
        } else {
            openrouterCustomModelInput.style.display = "none";
        }
    });
}

let currentLoadedSettings = {};

providerSelect.addEventListener("change", () => {
    const val = providerSelect.value;
    if (val === "gemini") {
        modelLabel.textContent = "Gemini Model";
        modelInput.value = currentLoadedSettings.gemini_model || "gemini-2.5-flash";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Gemini API Key";
        apiKeyInput.value = currentLoadedSettings.gemini_api_key || "";
        apiKeyInput.placeholder = "Optional if set in .env";
        baseUrlGroup.style.display = "none";
    } else if (val === "openai") {
        modelLabel.textContent = "OpenAI Model";
        modelInput.value = currentLoadedSettings.openai_model || "gpt-4o-mini";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "OpenAI API Key";
        apiKeyInput.value = currentLoadedSettings.openai_api_key || "";
        apiKeyInput.placeholder = "Optional if set in .env";
        baseUrlGroup.style.display = "none";
    } else if (val === "ollama") {
        modelLabel.textContent = "Ollama Model";
        modelInput.value = currentLoadedSettings.ollama_model || "qwen2.5-coder:7b";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "none";
        baseUrlGroup.style.display = "flex";
        if (baseUrlLabel) baseUrlLabel.textContent = "Ollama Base URL";
        baseUrlInput.value = currentLoadedSettings.ollama_base_url || "http://localhost:11434";
    } else if (val === "claude") {
        modelLabel.textContent = "Claude Model";
        modelInput.value = currentLoadedSettings.claude_model || "claude-3-5-sonnet-latest";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Anthropic API Key";
        apiKeyInput.value = currentLoadedSettings.anthropic_api_key || "";
        apiKeyInput.placeholder = "Optional if set in .env";
        baseUrlGroup.style.display = "none";
    } else if (val === "openrouter") {
        modelLabel.textContent = "OpenRouter Model";
        modelInput.style.display = "none";
        
        const openrouterModel = currentLoadedSettings.openrouter_model || "google/gemini-2.5-flash";
        if (openrouterModelSelect) {
            openrouterModelSelect.style.display = "block";
            let exists = false;
            for (let option of openrouterModelSelect.options) {
                if (option.value === openrouterModel) {
                    exists = true;
                    break;
                }
            }
            if (exists) {
                openrouterModelSelect.value = openrouterModel;
                if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
            } else {
                openrouterModelSelect.value = "custom";
                if (openrouterCustomModelInput) {
                    openrouterCustomModelInput.style.display = "block";
                    openrouterCustomModelInput.value = openrouterModel;
                }
            }
        }
        
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "OpenRouter API Key";
        apiKeyInput.value = currentLoadedSettings.openrouter_api_key || "";
        apiKeyInput.placeholder = "sk-or-v1-...";
        baseUrlGroup.style.display = "flex";
        if (baseUrlLabel) baseUrlLabel.textContent = "OpenRouter Base URL";
        baseUrlInput.value = currentLoadedSettings.openrouter_base_url || "https://openrouter.ai/api/v1";
    } else if (val === "groq") {
        modelLabel.textContent = "Groq Model";
        modelInput.value = currentLoadedSettings.groq_model || "llama-3.3-70b-specdec";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Groq API Key";
        apiKeyInput.value = currentLoadedSettings.groq_api_key || "";
        apiKeyInput.placeholder = "gsk_...";
        baseUrlGroup.style.display = "none";
    } else if (val === "deepseek") {
        modelLabel.textContent = "DeepSeek Model";
        modelInput.value = currentLoadedSettings.deepseek_model || "deepseek-chat";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "DeepSeek API Key";
        apiKeyInput.value = currentLoadedSettings.deepseek_api_key || "";
        apiKeyInput.placeholder = "sk-...";
        baseUrlGroup.style.display = "none";
    } else if (val === "together") {
        modelLabel.textContent = "Together Model";
        modelInput.value = currentLoadedSettings.together_model || "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Together API Key";
        apiKeyInput.value = currentLoadedSettings.together_api_key || "";
        apiKeyInput.placeholder = "Together key";
        baseUrlGroup.style.display = "none";
    } else if (val === "mistral") {
        modelLabel.textContent = "Mistral Model";
        modelInput.value = currentLoadedSettings.mistral_model || "codestral-latest";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Mistral API Key";
        apiKeyInput.value = currentLoadedSettings.mistral_api_key || "";
        apiKeyInput.placeholder = "Mistral key";
        baseUrlGroup.style.display = "none";
    } else if (val === "cohere") {
        modelLabel.textContent = "Cohere Model";
        modelInput.value = currentLoadedSettings.cohere_model || "command-r-plus";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Cohere API Key";
        apiKeyInput.value = currentLoadedSettings.cohere_api_key || "";
        apiKeyInput.placeholder = "Cohere key";
        baseUrlGroup.style.display = "none";
    } else if (val === "xai") {
        modelLabel.textContent = "xAI (Grok) Model";
        modelInput.value = currentLoadedSettings.xai_model || "grok-2";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "xAI API Key";
        apiKeyInput.value = currentLoadedSettings.xai_api_key || "";
        apiKeyInput.placeholder = "xai-...";
        baseUrlGroup.style.display = "none";
    } else if (val === "azure") {
        modelLabel.textContent = "Azure Deployment Name";
        modelInput.value = currentLoadedSettings.azure_model || "gpt-4o";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Azure API Key";
        apiKeyInput.value = currentLoadedSettings.azure_api_key || "";
        apiKeyInput.placeholder = "Azure key";
        baseUrlGroup.style.display = "flex";
        if (baseUrlLabel) baseUrlLabel.textContent = "Azure Endpoint URL";
        baseUrlInput.value = currentLoadedSettings.azure_endpoint || "";
    } else if (val === "bedrock") {
        modelLabel.textContent = "AWS Bedrock Model ID";
        modelInput.value = currentLoadedSettings.bedrock_model || "anthropic.claude-3-5-sonnet-20240620-v1:0";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "none";
        baseUrlGroup.style.display = "flex";
        if (baseUrlLabel) baseUrlLabel.textContent = "AWS Region";
        baseUrlInput.value = currentLoadedSettings.bedrock_region || "us-east-1";
    } else if (val === "zai") {
        modelLabel.textContent = "Z.ai Model";
        modelInput.value = currentLoadedSettings.zai_model || "glm-4-flash";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "Z.ai API Key";
        apiKeyInput.value = currentLoadedSettings.zai_api_key || "";
        apiKeyInput.placeholder = "Z.ai Key";
        baseUrlGroup.style.display = "none";
    } else if (val === "omnirouter") {
        modelLabel.textContent = "OmniRouter Model";
        modelInput.value = currentLoadedSettings.omnirouter_model || "meta-llama/llama-3.3-70b-instruct";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "OmniRouter API Key";
        apiKeyInput.value = currentLoadedSettings.omnirouter_api_key || "";
        apiKeyInput.placeholder = "Optional local API key";
        baseUrlGroup.style.display = "flex";
        if (baseUrlLabel) baseUrlLabel.textContent = "OmniRouter Base URL";
        baseUrlInput.value = currentLoadedSettings.omnirouter_base_url || "http://localhost:20128/v1";
    } else if (val === "nvidia") {
        modelLabel.textContent = "NVIDIA Model ID";
        modelInput.value = currentLoadedSettings.nvidia_model || "nvidia/llama-3.1-nemotron-70b-instruct";
        modelInput.style.display = "block";
        if (openrouterModelSelect) openrouterModelSelect.style.display = "none";
        if (openrouterCustomModelInput) openrouterCustomModelInput.style.display = "none";
        apiKeyGroup.style.display = "flex";
        apiKeyLabel.textContent = "NVIDIA API Key";
        apiKeyInput.value = currentLoadedSettings.nvidia_api_key || "";
        apiKeyInput.placeholder = "nvapi-...";
        baseUrlGroup.style.display = "none";
    }
});

// Synchronize client-side cache dynamically when inputs change
modelInput.addEventListener("input", () => {
    const val = providerSelect.value;
    if (val === "gemini") currentLoadedSettings.gemini_model = modelInput.value.trim();
    else if (val === "openai") currentLoadedSettings.openai_model = modelInput.value.trim();
    else if (val === "ollama") currentLoadedSettings.ollama_model = modelInput.value.trim();
    else if (val === "claude") currentLoadedSettings.claude_model = modelInput.value.trim();
    else if (val === "groq") currentLoadedSettings.groq_model = modelInput.value.trim();
    else if (val === "deepseek") currentLoadedSettings.deepseek_model = modelInput.value.trim();
    else if (val === "together") currentLoadedSettings.together_model = modelInput.value.trim();
    else if (val === "mistral") currentLoadedSettings.mistral_model = modelInput.value.trim();
    else if (val === "cohere") currentLoadedSettings.cohere_model = modelInput.value.trim();
    else if (val === "xai") currentLoadedSettings.xai_model = modelInput.value.trim();
    else if (val === "azure") currentLoadedSettings.azure_model = modelInput.value.trim();
    else if (val === "bedrock") currentLoadedSettings.bedrock_model = modelInput.value.trim();
    else if (val === "zai") currentLoadedSettings.zai_model = modelInput.value.trim();
    else if (val === "omnirouter") currentLoadedSettings.omnirouter_model = modelInput.value.trim();
    else if (val === "nvidia") currentLoadedSettings.nvidia_model = modelInput.value.trim();
});

if (openrouterModelSelect) {
    openrouterModelSelect.addEventListener("change", () => {
        if (openrouterModelSelect.value !== "custom") {
            currentLoadedSettings.openrouter_model = openrouterModelSelect.value;
        } else if (openrouterCustomModelInput) {
            currentLoadedSettings.openrouter_model = openrouterCustomModelInput.value.trim();
        }
    });
}
if (openrouterCustomModelInput) {
    openrouterCustomModelInput.addEventListener("input", () => {
        currentLoadedSettings.openrouter_model = openrouterCustomModelInput.value.trim();
    });
}

apiKeyInput.addEventListener("input", () => {
    const val = providerSelect.value;
    if (val === "gemini") currentLoadedSettings.gemini_api_key = apiKeyInput.value.trim();
    else if (val === "openai") currentLoadedSettings.openai_api_key = apiKeyInput.value.trim();
    else if (val === "claude") currentLoadedSettings.anthropic_api_key = apiKeyInput.value.trim();
    else if (val === "openrouter") currentLoadedSettings.openrouter_api_key = apiKeyInput.value.trim();
    else if (val === "groq") currentLoadedSettings.groq_api_key = apiKeyInput.value.trim();
    else if (val === "deepseek") currentLoadedSettings.deepseek_api_key = apiKeyInput.value.trim();
    else if (val === "together") currentLoadedSettings.together_api_key = apiKeyInput.value.trim();
    else if (val === "mistral") currentLoadedSettings.mistral_api_key = apiKeyInput.value.trim();
    else if (val === "cohere") currentLoadedSettings.cohere_api_key = apiKeyInput.value.trim();
    else if (val === "xai") currentLoadedSettings.xai_api_key = apiKeyInput.value.trim();
    else if (val === "azure") currentLoadedSettings.azure_api_key = apiKeyInput.value.trim();
    else if (val === "zai") currentLoadedSettings.zai_api_key = apiKeyInput.value.trim();
    else if (val === "omnirouter") currentLoadedSettings.omnirouter_api_key = apiKeyInput.value.trim();
    else if (val === "nvidia") currentLoadedSettings.nvidia_api_key = apiKeyInput.value.trim();
});

baseUrlInput.addEventListener("input", () => {
    const val = providerSelect.value;
    if (val === "ollama") currentLoadedSettings.ollama_base_url = baseUrlInput.value.trim();
    else if (val === "openrouter") currentLoadedSettings.openrouter_base_url = baseUrlInput.value.trim();
    else if (val === "azure") currentLoadedSettings.azure_endpoint = baseUrlInput.value.trim();
    else if (val === "bedrock") currentLoadedSettings.bedrock_region = baseUrlInput.value.trim();
    else if (val === "omnirouter") currentLoadedSettings.omnirouter_base_url = baseUrlInput.value.trim();
});

if (approvalModeSelect) {
    approvalModeSelect.addEventListener("change", () => {
        currentLoadedSettings.approval_mode = approvalModeSelect.value;
    });
}

const coderProviderSelect = document.getElementById("coder-provider-select");
const coderCliCommandGroup = document.getElementById("coder-cli-command-group");
const coderCliCommandInput = document.getElementById("coder-cli-command-input");

if (coderProviderSelect) {
    coderProviderSelect.addEventListener("change", () => {
        const val = coderProviderSelect.value;
        currentLoadedSettings.coder_provider = val;
        if (coderCliCommandGroup) {
            if (val === "cli") {
                coderCliCommandGroup.style.display = "block";
            } else {
                coderCliCommandGroup.style.display = "none";
            }
        }
        saveSettingsOnUIChange();
    });
}

if (coderCliCommandInput) {
    coderCliCommandInput.addEventListener("input", () => {
        currentLoadedSettings.coder_cli_command = coderCliCommandInput.value.trim();
    });
}

if (semanticCacheToggle) {
    semanticCacheToggle.addEventListener("change", () => {
        saveSettingsOnUIChange();
    });
}

// Slider iteration value label
iterationsSlider.addEventListener("input", () => {
    iterationsVal.textContent = iterationsSlider.value;
});

// Clear console
clearLogsBtn.addEventListener("click", () => {
    if (term) term.clear();
    if (termConsole) termConsole.clear();
    lastLogCount = 0;
});

const retryBtnWrap = document.getElementById("retry-btn-wrap");

// Run agent trigger
function triggerAgentRun(promptText, startFresh = false) {
    startBtn.disabled = true;
    startBtn.className = "studio-action-icon-btn studio-action-run";
    startBtn.innerHTML = '<span class="btn-spinner" style="width:18px;height:18px;"></span><span class="action-label">Running...</span>';
    
    runningPrompt = promptText;
    isAgentRunning = true;
    wasAgentRunning = true;
    
    if (retryBtnWrap) retryBtnWrap.style.display = "none";
    
    fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt: promptText,
            provider: providerSelect.value,
            model: modelInput.value.trim(),
            api_key: apiKeyInput.value.trim() || null,
            base_url: baseUrlInput.value.trim() || null,
            max_iterations: parseInt(iterationsSlider.value),
            parent_id: currentActiveParentId,
            start_fresh: startFresh
        })
    })
    .then(r => {
        if (!r.ok) {
            return r.json().then(err => { throw new Error(err.detail || "Failed to start agent") });
        }
        return r.json();
    })
    .then(data => {
        console.log("Agent started:", data);
        if (data.history_id) {
            currentActiveParentId = data.history_id;
        }
        // Clear logs and tree variables for fresh start
        if (termConsole) {
            termConsole.clear();
            termConsole.write("Initiating Multi-Agent Software Agency...\r\n");
        }
        switchTerminalTab("console");
        lastLogCount = 0;
        fileTree.innerHTML = '<div class="tree-placeholder">Scanning workspace...</div>';
        existingFiles = [];
        
        // Immediate poll
        pollStatus();
        // Start polling interval
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(pollStatus, 1500);
    })
    .catch(err => {
        alert(err.message);
        startBtn.disabled = false;
        startBtn.className = "studio-action-icon-btn studio-action-run";
        startBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="22" height="22"><path d="M13 2L4.09 12.26a1 1 0 0 0-.09 1.05A1 1 0 0 0 5 14h6v8l8.91-10.26a1 1 0 0 0 .09-1.05A1 1 0 0 0 19 10h-6V2z"/></svg><span class="action-label">Run Studio</span><div class="studio-action-tooltip">⚡ Run Studio<br><small>Execute agents on your requirements</small></div>';
        isAgentRunning = false;
    });
}

startBtn.addEventListener("click", () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
        alert("Please specify application requirements first!");
        return;
    }
    
    // Check if it is currently in "Apply & Restart" state
    if (startBtn.innerHTML.includes("Apply & Restart")) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="btn-spinner"></span> Restarting Studio...';
        
        // Terminate active agent
        fetch("/api/terminate", { method: "POST" })
        .then(r => r.json())
        .then(() => {
            // Poll status until not running, then trigger the new run
            let checkInterval = setInterval(() => {
                fetch("/api/status")
                .then(r => r.json())
                .then(status => {
                    if (!status.running) {
                        clearInterval(checkInterval);
                        triggerAgentRun(prompt);
                    }
                });
            }, 500);
        })
        .catch(err => {
            alert("Failed to restart: " + err);
            pollStatus();
        });
        return;
    }
    
    // Normal start
    triggerAgentRun(prompt);
});

if (promptInput) {
    promptInput.addEventListener("input", () => {
        if (isAgentRunning) {
            const currentPrompt = promptInput.value.trim();
            if (currentPrompt !== runningPrompt) {
                // User has modified the prompt while the agent is running
                startBtn.disabled = false;
                startBtn.className = "studio-action-icon-btn studio-action-retry";
                startBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg><span class="action-label">Apply & Restart</span><div class="studio-action-tooltip">🔄 Apply &amp; Restart<br><small>Stop running and re-run with new prompt</small></div>';
            } else {
                startBtn.disabled = true;
                startBtn.className = "studio-action-icon-btn studio-action-run";
                startBtn.innerHTML = '<span class="btn-spinner" style="width:18px;height:18px;"></span><span class="action-label">Running...</span>';
            }
        }
    });
}

if (retryBtn) {
    retryBtn.addEventListener("click", () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Please specify application requirements first!");
            return;
        }
        triggerAgentRun(prompt);
    });
}

// HITL APPROVAL LISTENERS
hitlApproveBtn.addEventListener("click", () => {
    hitlApproveBtn.disabled = true;
    hitlRejectBtn.disabled = true;
    
    fetch("/api/approve", { method: "POST" })
    .then(r => r.json())
    .then(d => {
        hitlModal.style.display = "none";
        hitlApproveBtn.disabled = false;
        hitlRejectBtn.disabled = false;
    })
    .catch(err => {
        alert("Failed to send approval: " + err);
        hitlApproveBtn.disabled = false;
        hitlRejectBtn.disabled = false;
    });
});

hitlRejectBtn.addEventListener("click", () => {
    const feedback = hitlFeedbackInput.value.trim();
    if (!feedback) {
        alert("Please specify revision feedback instructions so the agent knows what to fix!");
        return;
    }
    
    hitlApproveBtn.disabled = true;
    hitlRejectBtn.disabled = true;
    
    fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback: feedback })
    })
    .then(r => r.json())
    .then(d => {
        hitlModal.style.display = "none";
        hitlFeedbackInput.value = "";
        hitlApproveBtn.disabled = false;
        hitlRejectBtn.disabled = false;
    })
    .catch(err => {
        alert("Failed to send feedback: " + err);
        hitlApproveBtn.disabled = false;
        hitlRejectBtn.disabled = false;
    });
});

// PLAY / PAUSE BUTTONS LISTENERS
const pauseBtn = document.getElementById("pause-btn");
const resumeBtn = document.getElementById("resume-btn");

if (pauseBtn) {
    pauseBtn.addEventListener("click", () => {
        pauseBtn.disabled = true;
        pauseBtn.textContent = "⌛ Pausing...";
        fetch("/api/pause", { method: "POST" })
        .then(r => r.json())
        .then(() => pollStatus())
        .catch(err => {
            alert("Failed to pause: " + err);
            pauseBtn.disabled = false;
            pauseBtn.textContent = "⏸️ Pause";
        });
    });
}

if (resumeBtn) {
    resumeBtn.addEventListener("click", () => {
        fetch("/api/resume", { method: "POST" })
        .then(r => r.json())
        .then(() => pollStatus())
        .catch(err => alert("Failed to resume: " + err));
    });
}

const terminateBtn = document.getElementById("terminate-btn");
if (terminateBtn) {
    terminateBtn.addEventListener("click", () => {
        terminateBtn.disabled = true;
        terminateBtn.textContent = "⌛ Terminating...";
        fetch("/api/terminate", { method: "POST" })
        .then(r => r.json())
        .then(() => pollStatus())
        .catch(err => {
            alert("Failed to terminate: " + err);
            terminateBtn.disabled = false;
            terminateBtn.textContent = "🛑 Terminate";
        });
    });
}

// FUNCTIONS

function pollStatus() {
    fetch("/api/status")
    .then(r => r.json())
    .then(status => {
        updateStatusIndicator(status);
        appendLogs(status.logs);
        updateFileTree(status.files);
        handleHITLModal(status);
        
        // Update agent execution flow visualization flowchart nodes
        const activeAgent = status.active_agent || "idle";
        const nodeOrchestrator = document.getElementById("node-orchestrator");
        const nodeAnalyst = document.getElementById("node-analyst");
        const nodeImpact = document.getElementById("node-impact");
        const nodeProgrammer = document.getElementById("node-programmer");
        const nodeTester = document.getElementById("node-tester");
        const nodeDeployer = document.getElementById("node-deployer");
        
        const nodes = [
            { id: "orchestrator", el: nodeOrchestrator },
            { id: "analyst", el: nodeAnalyst },
            { id: "impact", el: nodeImpact },
            { id: "programmer", el: nodeProgrammer },
            { id: "tester", el: nodeTester },
            { id: "deployer", el: nodeDeployer }
        ];
        
        nodes.forEach(node => {
            if (!node.el) return;
            const statusPill = node.el.querySelector(".node-status-pill");
            
            if (activeAgent === "idle" || !status.running) {
                node.el.className = "flow-viz-node";
                if (statusPill) {
                    statusPill.textContent = "Idle";
                }
            } else if (activeAgent === node.id) {
                node.el.className = "flow-viz-node active";
                if (statusPill) {
                    statusPill.textContent = "Running";
                }
            } else {
                const pipeline = ["orchestrator", "analyst", "impact", "programmer", "tester", "deployer"];
                const activeIndex = pipeline.indexOf(activeAgent);
                const nodeIndex = pipeline.indexOf(node.id);
                
                if (nodeIndex !== -1 && activeIndex !== -1 && nodeIndex < activeIndex) {
                    node.el.className = "flow-viz-node completed";
                    if (statusPill) {
                        statusPill.textContent = "Done";
                    }
                } else {
                    node.el.className = "flow-viz-node";
                    if (statusPill) {
                        statusPill.textContent = "Idle";
                    }
                }
            }
        });
        
        if (activeFolderPath && status.active_workspace) {
            activeFolderPath.textContent = status.active_workspace;
        }
        
        // If simulation stopped, cleanup poll
        if (!status.running) {
            isAgentRunning = false;
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
            startBtn.disabled = false;
            startBtn.className = "studio-action-icon-btn studio-action-run";
            startBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="22" height="22"><path d="M13 2L4.09 12.26a1 1 0 0 0-.09 1.05A1 1 0 0 0 5 14h6v8l8.91-10.26a1 1 0 0 0 .09-1.05A1 1 0 0 0 19 10h-6V2z"/></svg><span class="action-label">Run Studio</span><div class="studio-action-tooltip">⚡ Run Studio<br><small>Execute agents on your requirements</small></div>';
            
            if (runningPrompt !== "" && retryBtnWrap) {
                retryBtnWrap.style.display = "flex";
            }
            
            // Load and display live web app preview on successful run
            if (status.preview_url) {
                if (previewUrlInput) previewUrlInput.value = status.preview_url;
                if (previewIframe) previewIframe.src = status.preview_url;
                if (tabPreview) tabPreview.click();
            }
            
            // Refresh Git logs and active branch details
            pollGitStatus();
            
            if (wasAgentRunning) {
                wasAgentRunning = false;
                
                // Determine if there was an error or limit reached
                const hasError = status.last_error && status.last_error.trim() !== "" && !status.last_error.includes("Simulation terminated by user");
                const hitLimit = status.iterations > 0 && status.max_iterations > 0 && status.iterations >= status.max_iterations;
                
                if (hasError || hitLimit) {
                    const contentContainer = document.getElementById("work-summary-content");
                    const modal = document.getElementById("work-summary-modal");
                    if (contentContainer && modal) {
                        let alertMarkdown = "";
                        if (hasError) {
                            alertMarkdown = `
# ⚠️ Simulation Stopped with Errors

The multi-agent workflow encountered an issue and could not complete all steps successfully.

> [!WARNING]
> **Fatal Error during execution:**
> \`\`\`
> ${status.last_error}
> \`\`\`

### 🔍 Suggestions:
* **Rate Limits / TPM**: If you see a \`429\` or \`413\` tokens per minute rate limit error, switch to a model/provider with higher limits (like **Google Gemini 2.5 Flash**).
* **Workspace Cleanliness**: Ensure your active workspace folder does not contain large directories like \`.venv\` or \`node_modules\`, as these consume your model's tokens per minute.
* **Credentials**: Verify your API keys under **LLM Settings**.
`;
                        } else if (hitLimit) {
                            alertMarkdown = `
# ⚠️ Iteration Limit Reached

The simulation reached the maximum allowed iteration limit before completing all tasks.

> [!IMPORTANT]
> **Limit Reached**: **${status.iterations}** out of **${status.max_iterations}** iterations performed.

### 🔍 Suggestions:
* **Increase Limit**: Drag the **Max Iterations** slider in the workspace sidebar to a higher count (e.g. 5 or 8) to give the agents more attempts to compile, run tests, and debug.
* **Refine Prompt**: Simplify your prompt requirements to make the tasks easier for the coder agent to solve.
`;
                        }
                        contentContainer.innerHTML = marked.parse(alertMarkdown);
                        modal.style.display = "flex";
                    }
                } else {
                    // Fetch walkthrough_agent.md on successful completion
                    fetch("/api/file?path=walkthrough_agent.md")
                    .then(r => {
                        if (r.ok) return r.json();
                        throw new Error("No walkthrough file found");
                    })
                    .then(data => {
                        if (data && data.content) {
                            const contentContainer = document.getElementById("work-summary-content");
                            const modal = document.getElementById("work-summary-modal");
                            if (contentContainer && modal) {
                                contentContainer.innerHTML = marked.parse(data.content);
                                modal.style.display = "flex";
                            }
                        }
                    })
                    .catch(err => {
                        console.log("No walkthrough summary generated for this run:", err);
                    });
                }
            }
        } else {
            isAgentRunning = true;
            if (status.preview_url && previewUrlInput) {
                previewUrlInput.value = status.preview_url;
            }
        }
    })
    .catch(err => {
        console.error("Polling error:", err);
    });
}

function updateStatusIndicator(status) {
    if (status.running) {
        if (terminateBtn) {
            terminateBtn.style.display = "inline-flex";
            terminateBtn.disabled = false;
            terminateBtn.textContent = "🛑 Terminate";
        }
        if (status.paused) {
            globalStatusDot.className = "status-dot waiting";
            globalStatusText.textContent = "Execution Paused";
            if (pauseBtn) pauseBtn.style.display = "none";
            if (resumeBtn) resumeBtn.style.display = "inline-flex";
        } else if (status.awaiting_approval) {
            globalStatusDot.className = "status-dot waiting";
            globalStatusText.textContent = "Awaiting Approval Checkpoint";
            if (pauseBtn) pauseBtn.style.display = "none";
            if (resumeBtn) resumeBtn.style.display = "none";
        } else {
            globalStatusDot.className = "status-dot running";
            globalStatusText.textContent = "Agent Working...";
            if (pauseBtn) {
                pauseBtn.style.display = "inline-flex";
                pauseBtn.disabled = false;
                pauseBtn.textContent = "⏸️ Pause";
            }
            if (resumeBtn) resumeBtn.style.display = "none";
        }
    } else {
        globalStatusDot.className = "status-dot";
        globalStatusText.textContent = "Idle";
        if (pauseBtn) pauseBtn.style.display = "none";
        if (resumeBtn) resumeBtn.style.display = "none";
        if (terminateBtn) terminateBtn.style.display = "none";
    }
}

function appendLogs(logs) {
    if (logs.length > lastLogCount) {
        const newLogs = logs.slice(lastLogCount);
        newLogs.forEach(log => {
            if (termConsole) {
                let colorizedLog = log;
                if (log.startsWith("[Orchestrator") || log.startsWith("[Router")) {
                    colorizedLog = "\x1b[36m" + log + "\x1b[0m";
                } else if (
                    log.startsWith("[Product Manager") || 
                    log.startsWith("[Business Analyst") || 
                    log.startsWith("[Architect") || 
                    log.startsWith("[Impact Analyzer") || 
                    log.startsWith("[Implement Engineer") || 
                    log.startsWith("[Developer") || 
                    log.startsWith("[QA Tester") || 
                    log.startsWith("[Deployment Agent")
                ) {
                    colorizedLog = "\x1b[35m" + log + "\x1b[0m";
                } else if (log.toLowerCase().includes("error") || log.toLowerCase().includes("fail")) {
                    colorizedLog = "\x1b[31m" + log + "\x1b[0m";
                } else if (log.toLowerCase().includes("success") || log.toLowerCase().includes("completed successfully")) {
                    colorizedLog = "\x1b[32m" + log + "\x1b[0m";
                } else if (log.toLowerCase().includes("warning")) {
                    colorizedLog = "\x1b[33m" + log + "\x1b[0m";
                }
                termConsole.write(colorizedLog + "\r\n");
            }
        });
        lastLogCount = logs.length;
    }
}

function buildTreeObject(files) {
    const root = {};
    files.forEach(filepath => {
        const parts = filepath.split('/');
        let current = root;
        parts.forEach((part, index) => {
            if (index === parts.length - 1) {
                // It's a file
                current[part] = { _type: 'file', path: filepath };
            } else {
                // It's a folder
                if (!current[part]) {
                    current[part] = { _type: 'folder', children: {} };
                }
                current = current[part].children;
            }
        });
    });
    return root;
}

function renderTree(node, parentElement) {
    const keys = Object.keys(node).sort((a, b) => {
        const aType = node[a]._type;
        const bType = node[b]._type;
        if (aType === bType) return a.localeCompare(b);
        return aType === 'folder' ? -1 : 1;
    });

    keys.forEach(key => {
        const val = node[key];
        if (val._type === 'folder') {
            const folderDiv = document.createElement("div");
            folderDiv.className = "tree-folder-node";
            
            const header = document.createElement("div");
            header.className = "folder-header";
            header.innerHTML = `<span>▶</span> 📁 <span>${key}</span>`;
            
            const childrenDiv = document.createElement("div");
            childrenDiv.className = "folder-children collapsed";
            
            header.addEventListener("click", (e) => {
                e.stopPropagation();
                childrenDiv.classList.toggle("collapsed");
                const arrow = header.querySelector("span");
                if (childrenDiv.classList.contains("collapsed")) {
                    arrow.textContent = "▶";
                } else {
                    arrow.textContent = "▼";
                }
            });
            
            renderTree(val.children, childrenDiv);
            
            folderDiv.appendChild(header);
            folderDiv.appendChild(childrenDiv);
            parentElement.appendChild(folderDiv);
        } else {
            const fileDiv = document.createElement("div");
            fileDiv.className = "tree-file-node";
            fileDiv.dataset.path = val.path;
            
            if (currentActiveFile === val.path) {
                fileDiv.classList.add("active");
            }
            
            fileDiv.innerHTML = `
                <div class="file-node-label">📄 <span>${key}</span></div>
                <button class="file-delete-btn" title="Delete File">🗑️</button>
            `;
            
            fileDiv.addEventListener("click", (e) => {
                selectFile(val.path, fileDiv);
            });
            
            const deleteBtn = fileDiv.querySelector(".file-delete-btn");
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                showFileDeleteConfirmation(val.path);
            });
            
            parentElement.appendChild(fileDiv);
        }
    });
}

function deleteFile(path) {
    fetch("/api/file/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: path })
    })
    .then(r => {
        if (!r.ok) throw new Error("Failed to delete file");
        return r.json();
    })
    .then(d => {
        if (currentActiveFile === path) {
            currentActiveFile = null;
            const activeFilenameNode = document.getElementById("active-filename");
            if (activeFilenameNode) updateActiveFilenameUI(null);
            if (codeEditor) codeEditor.setValue("");
            if (copyCodeBtn) copyCodeBtn.style.display = "none";
            if (saveCodeBtn) saveCodeBtn.style.display = "none";
        }
        pollStatus();
    })
    .catch(err => alert(err.message));
}

function updateFileTree(files) {
    // Update badge count
    const fileCountBadge = document.getElementById("file-count");
    if (fileCountBadge) {
        fileCountBadge.textContent = `${files.length} Files`;
    }

    // Check if files array is different from current
    if (JSON.stringify(files) === JSON.stringify(existingFiles)) {
        // Highlight active if it was updated
        document.querySelectorAll(".tree-file-node").forEach(el => {
            if (el.dataset.path === currentActiveFile) {
                el.classList.add("active");
            } else {
                el.classList.remove("active");
            }
        });
        return;
    }
    
    existingFiles = files;
    fileTree.innerHTML = "";
    
    if (files.length === 0) {
        fileTree.innerHTML = '<div class="tree-placeholder">No files in workspace yet.</div>';
        return;
    }
    
    const treeObj = buildTreeObject(files);
    renderTree(treeObj, fileTree);
}

function selectFile(filepath, element) {
    if (!filepath) return;
    
    // Save current active file to memory
    if (currentActiveFile && openFiles[currentActiveFile] && codeEditor) {
        openFiles[currentActiveFile].content = codeEditor.getValue();
    }
    
    currentActiveFile = filepath;
    updateActiveFilenameUI(filepath);
    
    // If already open in memory, load it immediately
    if (openFiles[filepath]) {
        if (codeEditor) {
            codeEditor.setOption("mode", openFiles[filepath].mode);
            codeEditor.setValue(openFiles[filepath].content);
        }
        if (copyCodeBtn) copyCodeBtn.style.display = "inline-flex";
        if (saveCodeBtn) saveCodeBtn.style.display = "inline-flex";
        renderTabs();
        return;
    }
    
    // Otherwise, fetch content from API
    if (codeEditor) codeEditor.setValue("Loading file content...");
    if (copyCodeBtn) copyCodeBtn.style.display = "none";
    if (saveCodeBtn) saveCodeBtn.style.display = "none";
    
    fetch(`/api/file?path=${encodeURIComponent(filepath)}`)
    .then(r => {
        if (!r.ok) throw new Error("Failed to load file");
        return r.json();
    })
    .then(data => {
        if (!codeEditor) return;
        
        // Determine file highlight mode
        const ext = filepath.split('.').pop().toLowerCase();
        let mode = "text/plain";
        if (ext === "py") mode = "python";
        else if (ext === "js" || ext === "json") mode = "javascript";
        else if (ext === "html" || ext === "cshtml") mode = "htmlmixed";
        else if (ext === "css") mode = "css";
        else if (ext === "cs") mode = "text/x-csharp";
        
        openFiles[filepath] = {
            content: data.content,
            isDirty: false,
            mode: mode
        };
        
        codeEditor.setOption("mode", mode);
        codeEditor.setValue(data.content);
        
        if (copyCodeBtn) copyCodeBtn.style.display = "inline-flex";
        if (saveCodeBtn) saveCodeBtn.style.display = "inline-flex";
        renderTabs();
    })
    .catch(err => {
        if (codeEditor) codeEditor.setValue("Error loading file: " + err.message);
    });
}

function renderTabs() {
    if (!editorTabsBar) return;
    editorTabsBar.innerHTML = "";
    
    const filepaths = Object.keys(openFiles);
    if (filepaths.length === 0) {
        updateActiveFilenameUI(null);
        if (copyCodeBtn) copyCodeBtn.style.display = "none";
        if (saveCodeBtn) saveCodeBtn.style.display = "none";
        return;
    }
    
    filepaths.forEach(fp => {
        const tabEl = document.createElement("div");
        tabEl.className = "file-tab";
        if (fp === currentActiveFile) {
            tabEl.classList.add("active");
        }
        
        const nameSpan = document.createElement("span");
        nameSpan.className = "file-tab-name";
        nameSpan.textContent = fp.split(/[\\/]/).pop();
        nameSpan.title = fp;
        nameSpan.style.fontSize = "11px";
        nameSpan.style.fontFamily = "monospace";
        tabEl.appendChild(nameSpan);
        
        // Dirty indicator
        if (openFiles[fp].isDirty) {
            const dot = document.createElement("span");
            dot.className = "file-tab-dirty-indicator";
            tabEl.appendChild(dot);
        }
        
        // Close icon
        const closeSpan = document.createElement("span");
        closeSpan.className = "file-tab-close";
        closeSpan.textContent = "✕";
        closeSpan.title = "Close file";
        closeSpan.style.fontSize = "11px";
        closeSpan.addEventListener("click", (e) => {
            e.stopPropagation();
            closeFileTab(fp);
        });
        tabEl.appendChild(closeSpan);
        
        tabEl.addEventListener("click", () => {
            selectFile(fp);
        });
        
        editorTabsBar.appendChild(tabEl);
    });
    
    // Toggle active state in sidebar
    document.querySelectorAll(".tree-file-node").forEach(el => {
        if (el.dataset.path === currentActiveFile) {
            el.classList.add("active");
        } else {
            el.classList.remove("active");
        }
    });
}

function closeFileTab(filepath) {
    if (openFiles[filepath] && openFiles[filepath].isDirty) {
        appConfirm(
            `Discard unsaved changes to ${filepath.split(/[\\/]/).pop()}?`,
            () => {
                performCloseFileTab(filepath);
            },
            null,
            "Discard Changes",
            "Keep Editing",
            "Unsaved Changes",
            "⚠️"
        );
    } else {
        performCloseFileTab(filepath);
    }
}

function performCloseFileTab(filepath) {
    delete openFiles[filepath];
    
    if (currentActiveFile === filepath) {
        const remaining = Object.keys(openFiles);
        if (remaining.length > 0) {
            const nextFile = remaining[remaining.length - 1];
            currentActiveFile = nextFile;
            updateActiveFilenameUI(nextFile);
            if (codeEditor) {
                codeEditor.setOption("mode", openFiles[nextFile].mode);
                codeEditor.setValue(openFiles[nextFile].content);
            }
            if (copyCodeBtn) copyCodeBtn.style.display = "inline-flex";
            if (saveCodeBtn) saveCodeBtn.style.display = "inline-flex";
        } else {
            currentActiveFile = null;
            updateActiveFilenameUI(null);
            if (codeEditor) codeEditor.setValue("");
            if (copyCodeBtn) copyCodeBtn.style.display = "none";
            if (saveCodeBtn) saveCodeBtn.style.display = "none";
        }
    }
    renderTabs();
}

function handleHITLModal(status) {
    if (status.awaiting_approval) {
        // Show modal if not already visible
        if (hitlModal.style.display !== "flex") {
            hitlModal.style.display = "flex";
            hitlStageTitle.textContent = status.approval_stage;
            hitlFeedbackInput.value = ""; // Reset feedback box
            
            // Render specifications markdown safely
            if (typeof marked !== "undefined") {
                hitlMarkdownContent.innerHTML = marked.parse(status.approval_text);
            } else {
                hitlMarkdownContent.textContent = status.approval_text;
            }
        }
    } else {
        hitlModal.style.display = "none";
    }
}

// Initial status pull on page load
pollStatus();
// Keep polling on load to catch active agents if server restarted
pollingInterval = setInterval(pollStatus, 2500);

// COLLAPSE / EXPAND TOGGLE HANDLERS

// 1. Sidebar Config Collapse
// Tabbed Page Routing Triggers
const navWorkspaceBtn = document.getElementById("nav-workspace-btn");
const navSettingsBtn = document.getElementById("nav-settings-btn");
const navHistoryBtn = document.getElementById("nav-history-btn");
const navTelemetryBtn = document.getElementById("nav-telemetry-btn");
const viewWorkspace = document.getElementById("view-workspace");
const viewSettings = document.getElementById("view-settings");
const viewHistory = document.getElementById("view-history");
const viewTelemetry = document.getElementById("view-telemetry");
const historyTableBody = document.getElementById("history-table-body");
const clearAllHistoryBtn = document.getElementById("clear-all-history-btn");

if (navWorkspaceBtn && navSettingsBtn && navHistoryBtn && viewWorkspace && viewSettings && viewHistory) {
    navWorkspaceBtn.addEventListener("click", () => {
        navWorkspaceBtn.classList.add("active");
        navSettingsBtn.classList.remove("active");
        navHistoryBtn.classList.remove("active");
        if (navTelemetryBtn) navTelemetryBtn.classList.remove("active");
        
        viewWorkspace.classList.add("active");
        viewSettings.classList.remove("active");
        viewHistory.classList.remove("active");
        if (viewTelemetry) viewTelemetry.classList.remove("active");
        
        // Refresh code editor dimension wrapping on tab swaps
        if (codeEditor) {
            codeEditor.refresh();
        }
    });

    navSettingsBtn.addEventListener("click", () => {
        navSettingsBtn.classList.add("active");
        navWorkspaceBtn.classList.remove("active");
        navHistoryBtn.classList.remove("active");
        if (navTelemetryBtn) navTelemetryBtn.classList.remove("active");
        
        viewSettings.classList.add("active");
        viewWorkspace.classList.remove("active");
        viewHistory.classList.remove("active");
        if (viewTelemetry) viewTelemetry.classList.remove("active");
    });

    navHistoryBtn.addEventListener("click", () => {
        navHistoryBtn.classList.add("active");
        navWorkspaceBtn.classList.remove("active");
        navSettingsBtn.classList.remove("active");
        if (navTelemetryBtn) navTelemetryBtn.classList.remove("active");
        
        viewHistory.classList.add("active");
        viewWorkspace.classList.remove("active");
        viewSettings.classList.remove("active");
        if (viewTelemetry) viewTelemetry.classList.remove("active");
        loadHistory();
    });
    
    if (navTelemetryBtn && viewTelemetry) {
        navTelemetryBtn.addEventListener("click", () => {
            navTelemetryBtn.classList.add("active");
            navWorkspaceBtn.classList.remove("active");
            navSettingsBtn.classList.remove("active");
            navHistoryBtn.classList.remove("active");
            
            viewTelemetry.classList.add("active");
            viewWorkspace.classList.remove("active");
            viewSettings.classList.remove("active");
            viewHistory.classList.remove("active");
            loadTelemetry();
        });
    }
}

// 2. File Explorer Collapse
const toggleExplorerBtn = document.getElementById("toggle-explorer-btn");
const workspaceBody = document.getElementById("workspace-body");

if (toggleExplorerBtn && workspaceBody) {
    toggleExplorerBtn.addEventListener("click", () => {
        workspaceBody.classList.toggle("explorer-collapsed");
        if (workspaceBody.classList.contains("explorer-collapsed")) {
            toggleExplorerBtn.classList.add("inactive");
            toggleExplorerBtn.title = "Show File Explorer";
        } else {
            toggleExplorerBtn.classList.remove("inactive");
            toggleExplorerBtn.title = "Hide File Explorer";
        }
    });
}

// 3. Developer Input Collapse
const toggleInputBtn = document.getElementById("toggle-input-btn");
const controlPanel = document.getElementById("control-panel");
const appBody = document.querySelector(".app-body");

if (toggleInputBtn && controlPanel && appBody) {
    toggleInputBtn.addEventListener("click", () => {
        controlPanel.classList.toggle("collapsed");
        appBody.classList.toggle("input-collapsed");
        if (controlPanel.classList.contains("collapsed")) {
            toggleInputBtn.textContent = "►";
            toggleInputBtn.title = "Expand Sidebar";
        } else {
            toggleInputBtn.textContent = "◄";
            toggleInputBtn.title = "Collapse Sidebar";
        }
        if (codeEditor) {
            codeEditor.refresh();
        }
    });
}

// 4. Terminal Collapse
const toggleTerminalBtn = document.getElementById("toggle-terminal-btn");
const mainContent = document.querySelector(".main-content");
const consoleBoxEl = document.getElementById("terminal-container");
const resizeHandleTerminalEl = document.getElementById("resize-handle-terminal");

if (toggleTerminalBtn && mainContent) {
    toggleTerminalBtn.addEventListener("click", () => {
        mainContent.classList.toggle("terminal-collapsed");
        if (mainContent.classList.contains("terminal-collapsed")) {
            mainContent.style.gridTemplateRows = "1fr 0px 50px";
            toggleTerminalBtn.textContent = "▲";
            toggleTerminalBtn.title = "Expand Terminal";
            if (consoleBoxEl) consoleBoxEl.style.display = "none";
            if (resizeHandleTerminalEl) resizeHandleTerminalEl.style.display = "none";
        } else {
            mainContent.style.gridTemplateRows = "1fr 6px 220px";
            toggleTerminalBtn.textContent = "▼";
            toggleTerminalBtn.title = "Collapse Terminal";
            if (consoleBoxEl) consoleBoxEl.style.display = "block";
            if (resizeHandleTerminalEl) resizeHandleTerminalEl.style.display = "block";
        }
        if (codeEditor) {
            codeEditor.refresh();
        }
    });
}

// FILE EXPLORER OPERATION BUTTONS

// New File Creator
const newFileBtn = document.getElementById("new-file-btn");
if (newFileBtn) {
    newFileBtn.addEventListener("click", () => {
        const name = prompt("Enter new file path (e.g. main.py, or subfolder/app.py):");
        if (!name) return;
        
        fetch("/api/file/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: name })
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail || "Failed to create file") });
            return r.json();
        })
        .then(() => pollStatus())
        .catch(err => alert(err.message));
    });
}

// New Folder Creator
const newFolderBtn = document.getElementById("new-folder-btn");
if (newFolderBtn) {
    newFolderBtn.addEventListener("click", () => {
        const name = prompt("Enter new folder path (e.g. tests, or src/components):");
        if (!name) return;
        
        fetch("/api/folder/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: name })
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail || "Failed to create folder") });
            return r.json();
        })
        .then(() => pollStatus())
        .catch(err => alert(err.message));
    });
}

// Reveal in System File Explorer
const revealOsBtn = document.getElementById("reveal-os-btn");
if (revealOsBtn) {
    revealOsBtn.addEventListener("click", () => {
        fetch("/api/file/reveal", { method: "POST" })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail || "Failed to reveal folder") });
            return r.json();
        })
        .catch(err => alert(err.message));
    });
}

// 4. File Explorer Width Draggable Resizer

const resizeHandle = document.getElementById("resize-handle");
let isResizing = false;

if (resizeHandle && workspaceBody) {
    resizeHandle.addEventListener("mousedown", (e) => {
        isResizing = true;
        resizeHandle.classList.add("active");
        document.body.style.cursor = "col-resize";
        e.preventDefault(); // Stop text highlighting selection
    });

    document.addEventListener("mousemove", (e) => {
        if (!isResizing) return;
        
        const containerRect = workspaceBody.getBoundingClientRect();
        // Width of file explorer is the distance from right side of container to cursor position
        let newExplorerWidth = containerRect.right - e.clientX;
        
        // Constrain explorer width (min 150px, max 450px)
        if (newExplorerWidth < 150) newExplorerWidth = 150;
        if (newExplorerWidth > 450) newExplorerWidth = 450;
        
        workspaceBody.style.gridTemplateColumns = `1fr 4px ${newExplorerWidth}px`;
        
        // Refresh CodeMirror layout dimensions so scrollbars fit perfectly
        if (codeEditor) {
            codeEditor.refresh();
        }
    });

    document.addEventListener("mouseup", () => {
        if (isResizing) {
            isResizing = false;
            resizeHandle.classList.remove("active");
            document.body.style.cursor = "default";
        }
    });
}

// 5. Terminal Height Draggable Resizer

const resizeHandleTerminal = document.getElementById("resize-handle-terminal");
let isResizingTerminal = false;

if (resizeHandleTerminal && mainContent) {
    resizeHandleTerminal.addEventListener("mousedown", (e) => {
        if (mainContent.classList.contains("terminal-collapsed")) {
            mainContent.classList.remove("terminal-collapsed");
            toggleTerminalBtn.textContent = "▼";
            toggleTerminalBtn.title = "Collapse Terminal";
            if (consoleBoxEl) consoleBoxEl.style.display = "block";
            if (resizeHandleTerminalEl) resizeHandleTerminalEl.style.display = "block";
        }
        isResizingTerminal = true;
        resizeHandleTerminal.classList.add("active");
        document.body.style.cursor = "row-resize";
        e.preventDefault(); // Stop text highlighting selection
    });

    document.addEventListener("mousemove", (e) => {
        if (!isResizingTerminal) return;
        
        const containerRect = mainContent.getBoundingClientRect();
        // Height of terminal is the distance from bottom of container to cursor position
        let newTerminalHeight = containerRect.bottom - e.clientY;
        
        // Constrain terminal height (min 100px, max 400px)
        if (newTerminalHeight < 100) newTerminalHeight = 100;
        if (newTerminalHeight > 400) newTerminalHeight = 400;
        
        mainContent.style.gridTemplateRows = `1fr 6px ${newTerminalHeight}px`;
        
        // Fit xterm terminals to new container dimensions
        if (fitAddon) { try { fitAddon.fit(); } catch(e) {} }
        if (fitAddonConsole) { try { fitAddonConsole.fit(); } catch(e) {} }
        
        // Refresh CodeMirror layout dimensions so scrollbars fit perfectly
        if (codeEditor) {
            codeEditor.refresh();
        }
    });

    document.addEventListener("mouseup", () => {
        if (isResizingTerminal) {
            isResizingTerminal = false;
            resizeHandleTerminal.classList.remove("active");
            document.body.style.cursor = "default";
        }
    });
}


let isInitialSettingsLoad = false;

function saveSettingsOnUIChange() {
    if (isInitialSettingsLoad) return;
    const val = providerSelect.value;
    currentLoadedSettings.provider = val;
    currentLoadedSettings.max_iterations = parseInt(iterationsSlider.value);
    currentLoadedSettings.approval_mode = approvalModeSelect.value;
    
    const coderProviderSelect = document.getElementById("coder-provider-select");
    const coderCliCommandInput = document.getElementById("coder-cli-command-input");
    if (coderProviderSelect) {
        currentLoadedSettings.coder_provider = coderProviderSelect.value;
    }
    if (coderCliCommandInput) {
        currentLoadedSettings.coder_cli_command = coderCliCommandInput.value.trim();
    }

    // Read values directly from UI inputs to prevent auto-fill or copy-paste synchronization lags
    if (val === "gemini") {
        currentLoadedSettings.gemini_model = modelInput.value.trim();
        currentLoadedSettings.gemini_api_key = apiKeyInput.value.trim();
    } else if (val === "openai") {
        currentLoadedSettings.openai_model = modelInput.value.trim();
        currentLoadedSettings.openai_api_key = apiKeyInput.value.trim();
    } else if (val === "ollama") {
        currentLoadedSettings.ollama_model = modelInput.value.trim();
        currentLoadedSettings.ollama_base_url = baseUrlInput.value.trim();
    } else if (val === "claude") {
        currentLoadedSettings.claude_model = modelInput.value.trim();
        currentLoadedSettings.anthropic_api_key = apiKeyInput.value.trim();
    } else if (val === "openrouter") {
        if (openrouterModelSelect && openrouterModelSelect.value !== "custom") {
            currentLoadedSettings.openrouter_model = openrouterModelSelect.value;
        } else if (openrouterCustomModelInput) {
            currentLoadedSettings.openrouter_model = openrouterCustomModelInput.value.trim();
        }
        currentLoadedSettings.openrouter_api_key = apiKeyInput.value.trim();
        currentLoadedSettings.openrouter_base_url = baseUrlInput.value.trim();
    } else if (val === "groq") {
        currentLoadedSettings.groq_model = modelInput.value.trim();
        currentLoadedSettings.groq_api_key = apiKeyInput.value.trim();
    } else if (val === "deepseek") {
        currentLoadedSettings.deepseek_model = modelInput.value.trim();
        currentLoadedSettings.deepseek_api_key = apiKeyInput.value.trim();
    } else if (val === "together") {
        currentLoadedSettings.together_model = modelInput.value.trim();
        currentLoadedSettings.together_api_key = apiKeyInput.value.trim();
    } else if (val === "mistral") {
        currentLoadedSettings.mistral_model = modelInput.value.trim();
        currentLoadedSettings.mistral_api_key = apiKeyInput.value.trim();
    } else if (val === "cohere") {
        currentLoadedSettings.cohere_model = modelInput.value.trim();
        currentLoadedSettings.cohere_api_key = apiKeyInput.value.trim();
    } else if (val === "xai") {
        currentLoadedSettings.xai_model = modelInput.value.trim();
        currentLoadedSettings.xai_api_key = apiKeyInput.value.trim();
    } else if (val === "azure") {
        currentLoadedSettings.azure_model = modelInput.value.trim();
        currentLoadedSettings.azure_api_key = apiKeyInput.value.trim();
        currentLoadedSettings.azure_endpoint = baseUrlInput.value.trim();
    } else if (val === "bedrock") {
        currentLoadedSettings.bedrock_model = modelInput.value.trim();
        currentLoadedSettings.bedrock_region = baseUrlInput.value.trim();
    } else if (val === "zai") {
        currentLoadedSettings.zai_model = modelInput.value.trim();
        currentLoadedSettings.zai_api_key = apiKeyInput.value.trim();
    } else if (val === "omnirouter") {
        currentLoadedSettings.omnirouter_model = modelInput.value.trim();
        currentLoadedSettings.omnirouter_api_key = apiKeyInput.value.trim();
        currentLoadedSettings.omnirouter_base_url = baseUrlInput.value.trim();
    } else if (val === "nvidia") {
        currentLoadedSettings.nvidia_model = modelInput.value.trim();
        currentLoadedSettings.nvidia_api_key = apiKeyInput.value.trim();
    }

    currentLoadedSettings.semantic_cache = semanticCacheToggle ? (semanticCacheToggle.checked ? "true" : "false") : "false";

    // Network settings
    const networkPortInput = document.getElementById('network-port-input');
    const networkHostInput = document.getElementById('network-host-input');
    const networkCorsInput = document.getElementById('network-cors-input');
    if (networkPortInput) {
        const portVal = parseInt(networkPortInput.value, 10);
        if (!isNaN(portVal) && portVal >= 1024 && portVal <= 65535) {
            currentLoadedSettings.network_port = portVal;
        }
    }
    if (networkHostInput) currentLoadedSettings.network_host = networkHostInput.value;
    if (networkCorsInput) currentLoadedSettings.network_cors_origins = networkCorsInput.value.trim();

    // Free Tier Rate Limiter settings
    const enableFreeLimitToggle = document.getElementById('enable-free-limit-toggle');
    const freeLimitRpmInput = document.getElementById('free-limit-rpm-input');
    if (enableFreeLimitToggle) {
        currentLoadedSettings.enable_free_limit = enableFreeLimitToggle.checked ? "true" : "false";
    }
    if (freeLimitRpmInput) {
        const rpmVal = parseInt(freeLimitRpmInput.value, 10);
        if (!isNaN(rpmVal) && rpmVal >= 1) {
            currentLoadedSettings.free_limit_rpm = rpmVal;
        }
    }

    fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentLoadedSettings)
    })
    .then(r => {
        if (r.ok) {
            if (saveStatusMsg) {
                saveStatusMsg.style.display = "inline";
                setTimeout(() => {
                    saveStatusMsg.style.display = "none";
                }, 3000);
            }
        }
    })
    .then(() => {
        const promptsPayload = {
            orchestrator: document.getElementById("prompt-orchestrator").value,
            analyst: document.getElementById("prompt-analyst").value,
            impact: document.getElementById("prompt-impact").value,
            programmer: document.getElementById("prompt-programmer").value,
            deployer: document.getElementById("prompt-deployer").value
        };
        return fetch("/api/settings/prompts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(promptsPayload)
        });
    })
    .catch(err => console.error("Failed to save settings: ", err));
}

function loadSettings() {
    isInitialSettingsLoad = true;
    fetch("/api/settings")
    .then(r => r.json())
    .then(settings => {
        if (!settings || Object.keys(settings).length === 0) {
            isInitialSettingsLoad = false;
            return;
        }
        currentLoadedSettings = settings;
        
        providerSelect.value = settings.provider || "gemini";
        providerSelect.dispatchEvent(new Event("change"));
        
        iterationsSlider.value = settings.max_iterations || 3;
        iterationsVal.textContent = iterationsSlider.value;
        
        if (approvalModeSelect) {
            approvalModeSelect.value = settings.approval_mode || "strict";
        }
        
        const coderProviderSelect = document.getElementById("coder-provider-select");
        const coderCliCommandInput = document.getElementById("coder-cli-command-input");
        if (coderProviderSelect) {
            coderProviderSelect.value = settings.coder_provider || "llm";
            coderProviderSelect.dispatchEvent(new Event("change"));
        }
        if (coderCliCommandInput) {
            coderCliCommandInput.value = settings.coder_cli_command || 'agy run "{prompt}"';
        }
        
        if (semanticCacheToggle) {
            semanticCacheToggle.checked = settings.semantic_cache === "true";
        }

        // Network settings
        const networkPortInput = document.getElementById('network-port-input');
        const networkHostInput = document.getElementById('network-host-input');
        const networkCorsInput = document.getElementById('network-cors-input');
        const networkCurrentUrl = document.getElementById('network-current-url');
        const networkUrlPreview = document.getElementById('network-url-preview');

        const savedPort = settings.network_port || 8000;
        const savedHost = settings.network_host || '0.0.0.0';
        const savedCors = settings.network_cors_origins || '*';

        if (networkPortInput) networkPortInput.value = savedPort;
        if (networkHostInput) networkHostInput.value = savedHost;
        if (networkCorsInput) networkCorsInput.value = savedCors;

        const currentUrl = `http://localhost:${savedPort}`;
        if (networkCurrentUrl) networkCurrentUrl.textContent = currentUrl;
        if (networkUrlPreview) networkUrlPreview.textContent = currentUrl;

        // Live port preview: update URL preview as user types
        if (networkPortInput && !networkPortInput._previewBound) {
            networkPortInput._previewBound = true;
            networkPortInput.addEventListener('input', () => {
                const p = parseInt(networkPortInput.value, 10);
                const previewUrl = (!isNaN(p) && p >= 1024 && p <= 65535)
                    ? `http://localhost:${p}` : 'Invalid port';
                if (networkUrlPreview) networkUrlPreview.textContent = previewUrl;
                // Highlight invalid
                networkPortInput.style.borderColor = (!isNaN(p) && p >= 1024 && p <= 65535)
                    ? 'var(--border-color)' : 'var(--danger)';
            });
        }

        // Free Tier Rate Limiter settings
        const enableFreeLimitToggle = document.getElementById('enable-free-limit-toggle');
        const freeLimitConfigPanel = document.getElementById('free-limit-config-panel');
        const freeLimitRpmInput = document.getElementById('free-limit-rpm-input');
        const freeLimitDelayPreview = document.getElementById('free-limit-delay-preview');

        const isFreeLimitEnabled = settings.enable_free_limit === "true";
        const savedRpm = settings.free_limit_rpm || 15;

        if (enableFreeLimitToggle) enableFreeLimitToggle.checked = isFreeLimitEnabled;
        if (freeLimitConfigPanel) freeLimitConfigPanel.style.display = isFreeLimitEnabled ? "flex" : "none";
        if (freeLimitRpmInput) freeLimitRpmInput.value = savedRpm;

        const updateFreeLimitPreview = () => {
            if (!freeLimitRpmInput || !freeLimitDelayPreview) return;
            const rpm = parseInt(freeLimitRpmInput.value, 10);
            if (!isNaN(rpm) && rpm >= 1) {
                const delay = (60.0 / rpm).toFixed(1);
                freeLimitDelayPreview.textContent = `~${delay} seconds / call`;
            } else {
                freeLimitDelayPreview.textContent = `Invalid RPM`;
            }
        };
        updateFreeLimitPreview();

        if (enableFreeLimitToggle && !enableFreeLimitToggle._bound) {
            enableFreeLimitToggle._bound = true;
            enableFreeLimitToggle.addEventListener('change', () => {
                if (freeLimitConfigPanel) {
                    freeLimitConfigPanel.style.display = enableFreeLimitToggle.checked ? "flex" : "none";
                }
                saveSettingsOnUIChange();
            });
        }
        if (freeLimitRpmInput && !freeLimitRpmInput._bound) {
            freeLimitRpmInput._bound = true;
            freeLimitRpmInput.addEventListener('input', () => {
                updateFreeLimitPreview();
                saveSettingsOnUIChange();
            });
        }

        isInitialSettingsLoad = false;
    })
    .then(() => loadCustomPrompts())
    .catch(err => {
        isInitialSettingsLoad = false;
        console.error("Failed to load settings: ", err);
    });
}

function loadHistory() {
    fetch("/api/history")
    .then(r => r.json())
    .then(history => {
        populateRecentPromptsDropdown(history);
        if (!historyTableBody) return;
        historyTableBody.innerHTML = "";
        if (history.length === 0) {
            historyTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No history records in database yet.</td></tr>`;
            return;
        }
        history.forEach(item => {
            const row = document.createElement("tr");
            
            const dateCell = document.createElement("td");
            dateCell.textContent = new Date(item.timestamp).toLocaleString();
            
            const modelCell = document.createElement("td");
            modelCell.textContent = `${item.provider} (${item.model})`;
            
            const promptCell = document.createElement("td");
            promptCell.className = "history-prompt-cell";
            promptCell.textContent = item.prompt;
            promptCell.title = "Click to load requirement prompt into Workspace";
            promptCell.addEventListener("click", () => {
                promptInput.value = item.prompt;
                currentActiveParentId = item.id;
                if (navWorkspaceBtn) navWorkspaceBtn.click();
            });
            
            const loopsCell = document.createElement("td");
            loopsCell.textContent = item.max_iterations;
            
            const statusCell = document.createElement("td");
            statusCell.innerHTML = `<span class="history-status-badge status-${item.status}">${item.status}</span>`;
            
            const actionCell = document.createElement("td");
            const delBtn = document.createElement("button");
            delBtn.className = "text-btn";
            delBtn.style.color = "var(--danger)";
            delBtn.textContent = "🗑️ Delete";
            delBtn.addEventListener("click", () => {
                appConfirm(
                    "Delete this requirement history record?",
                    () => {
                        deleteHistoryItem(item.id);
                    },
                    null,
                    "Delete Record",
                    "Cancel",
                    "Delete History Record",
                    "🗑️"
                );
            });
            actionCell.appendChild(delBtn);
            
            row.appendChild(dateCell);
            row.appendChild(modelCell);
            row.appendChild(promptCell);
            row.appendChild(loopsCell);
            row.appendChild(statusCell);
            row.appendChild(actionCell);
            historyTableBody.appendChild(row);
        });
    })
    .catch(err => console.error("Failed to load history: ", err));
}

function deleteHistoryItem(id) {
    fetch(`/api/history/${id}`, { method: "DELETE" })
    .then(r => r.json())
    .then(() => loadHistory())
    .catch(err => alert("Failed to delete record: " + err));
}

if (clearAllHistoryBtn) {
    clearAllHistoryBtn.addEventListener("click", () => {
        appConfirm(
            "Are you sure you want to clear all requirements history records? This cannot be undone.",
            () => {
                fetch("/api/history", { method: "DELETE" })
                .then(r => r.json())
                .then(() => loadHistory())
                .catch(err => alert("Failed to clear history: " + err));
            },
            null,
            "Clear History",
            "Cancel",
            "Clear Requirements History",
            "⚠️"
        );
    });
}

// Bind settings save configurations button click trigger
const saveSettingsBtn = document.getElementById("save-settings-btn");
const saveStatusMsg = document.getElementById("save-status-msg");

if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener("click", () => {
        saveSettingsOnUIChange();
    });
}

// Populate Recent Prompts Dropdown in Developer Input Sidebar
const recentPromptsTrigger = document.getElementById("recent-prompts-trigger");
const recentPromptsPopover = document.getElementById("recent-prompts-popover");
const recentPromptsList = document.getElementById("recent-prompts-list");

if (recentPromptsTrigger && recentPromptsPopover) {
    recentPromptsTrigger.addEventListener("click", (e) => {
        recentPromptsPopover.classList.toggle("show");
        e.stopPropagation();
    });

    // Close popover when clicking anywhere else
    document.addEventListener("click", (e) => {
        if (!recentPromptsPopover.contains(e.target) && e.target !== recentPromptsTrigger) {
            recentPromptsPopover.classList.remove("show");
        }
    });
}

function populateRecentPromptsDropdown(history) {
    if (!recentPromptsList) return;
    
    recentPromptsList.innerHTML = "";
    
    if (history.length === 0) {
        recentPromptsList.innerHTML = '<div class="popover-empty">No recent prompts.</div>';
        return;
    }
    
    // Limit to unique prompt descriptions to keep dropdown clean
    const uniquePrompts = [];
    
    history.forEach(item => {
        const p = item.prompt.trim();
        if (p && !uniquePrompts.includes(p)) {
            uniquePrompts.push(p);
            
            const itemDiv = document.createElement("div");
            itemDiv.className = "popover-item";
            
            const textSpan = document.createElement("span");
            textSpan.className = "popover-item-text";
            textSpan.textContent = p;
            
            const metaSpan = document.createElement("span");
            metaSpan.className = "popover-item-meta";
            
            // Format timestamp info
            const date = new Date(item.timestamp);
            const dateStr = date.toLocaleDateString();
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            metaSpan.textContent = `${dateStr} ${timeStr} • ${item.provider}`;
            
            itemDiv.appendChild(textSpan);
            itemDiv.appendChild(metaSpan);
            
            itemDiv.addEventListener("click", () => {
                promptInput.value = p;
                currentActiveParentId = item.id;
                recentPromptsPopover.classList.remove("show");
            });
            
            recentPromptsList.appendChild(itemDiv);
        }
    });
}

// Workspace Folder Management

const openFolderBtn = document.getElementById("open-folder-btn");
const activeFolderPath = document.getElementById("active-folder-path");

if (openFolderBtn) {
    openFolderBtn.addEventListener("click", () => {
        fetch("/api/workspace/select", { method: "POST" })
        .then(r => {
            if (!r.ok) return r.json().then(err => { throw new Error(err.detail || "Failed to open folder picker") });
            return r.json();
        })
        .then(res => {
            if (res.status === "cancelled" || !res.path) {
                return;
            }
            
            return fetch("/api/workspace/open", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: res.path })
            })
            .then(r => {
                if (!r.ok) return r.json().then(err => { throw new Error(err.detail || "Failed to open selected folder") });
                return r.json();
            })
            .then(data => {
                currentActiveParentId = null;
                if (activeFolderPath) {
                    activeFolderPath.textContent = data.active_workspace;
                }
                pollStatus();
            });
        })
        .catch(err => alert("Error: " + err.message));
    });
}

function loadActiveWorkspace() {
    fetch("/api/workspace/active")
    .then(r => r.json())
    .then(data => {
        if (activeFolderPath && data.active_workspace) {
            activeFolderPath.textContent = data.active_workspace;
        }
    })
    .catch(err => console.error("Failed to load active workspace: ", err));
}

// Startup initializations
loadSettings();
loadHistory(); // Calls populateRecentPromptsDropdown internally
loadActiveWorkspace();

// Live Web Preview & Git Status Integration
const tabEditor = document.getElementById("tab-editor");
const tabPreview = document.getElementById("tab-preview");
const editorTabContent = document.getElementById("editor-tab-content");
const previewTabContent = document.getElementById("preview-tab-content");
const previewUrlInput = document.getElementById("preview-url");
const previewIframe = document.getElementById("preview-iframe");
const previewReloadBtn = document.getElementById("preview-reload");
const previewOpenTabBtn = document.getElementById("preview-open-tab");

const gitBranchNameSpan = document.getElementById("git-branch-name");
const gitStatusBadge = document.getElementById("git-status-badge");

if (tabEditor && tabPreview && editorTabContent && previewTabContent) {
    tabEditor.addEventListener("click", () => {
        tabEditor.classList.add("active");
        tabPreview.classList.remove("active");
        editorTabContent.style.display = "flex";
        previewTabContent.style.display = "none";
        if (codeEditor) {
            codeEditor.refresh();
        }
    });

    tabPreview.addEventListener("click", () => {
        tabPreview.classList.add("active");
        tabEditor.classList.remove("active");
        previewTabContent.style.display = "flex";
        editorTabContent.style.display = "none";
        
        // Load iframe src if empty or different
        const currentUrl = previewUrlInput ? previewUrlInput.value.trim() : "";
        if (currentUrl && previewIframe && previewIframe.src !== currentUrl) {
            previewIframe.src = currentUrl;
        }
    });
}

if (previewReloadBtn && previewIframe && previewUrlInput) {
    previewReloadBtn.addEventListener("click", () => {
        const url = previewUrlInput.value.trim();
        if (url) {
            previewIframe.src = url;
        }
    });
}

if (previewOpenTabBtn && previewUrlInput) {
    previewOpenTabBtn.addEventListener("click", () => {
        const url = previewUrlInput.value.trim();
        if (url) {
            window.open(url, "_blank");
        }
    });
}

if (previewUrlInput) {
    previewUrlInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const url = previewUrlInput.value.trim();
            if (url && previewIframe) {
                previewIframe.src = url;
            }
        }
    });
}

function pollGitStatus() {
    fetch("/api/git/status")
    .then(r => {
        if (!r.ok) throw new Error("Git check failed");
        return r.json();
    })
    .then(data => {
        if (gitBranchNameSpan && gitStatusBadge) {
            if (data.branch && data.branch !== "unknown") {
                gitBranchNameSpan.textContent = data.branch;
                gitStatusBadge.style.display = "inline-flex";
            } else {
                gitStatusBadge.style.display = "none";
            }
        }
    })
    .catch(err => {
        console.warn("Failed to check Git status: ", err);
        if (gitStatusBadge) gitStatusBadge.style.display = "none";
    });
}

// Poll Git status on startup
pollGitStatus();

// Git Version Control Modal Center bindings and fetches
const gitModal = document.getElementById("git-modal");
const closeGitModalBtn = document.getElementById("close-git-modal");
const gitModalBranch = document.getElementById("git-modal-branch");
const gitModalStatusSummary = document.getElementById("git-modal-status-summary");
const gitModalChangesList = document.getElementById("git-modal-changes-list");
const gitModalCommitsList = document.getElementById("git-modal-commits-list");
const gitModalDiffBox = document.getElementById("git-modal-diff-box");

function openGitCenter() {
    if (!gitModal) return;
    
    // Show modal
    gitModal.style.display = "flex";
    
    loadGitBranches();
    
    if (gitModalBranch) gitModalBranch.textContent = "Checking branch...";
    if (gitModalStatusSummary) gitModalStatusSummary.textContent = "Loading status...";
    if (gitModalChangesList) gitModalChangesList.innerHTML = `<div style="color: var(--text-secondary); font-style: italic;">Loading status...</div>`;
    if (gitModalCommitsList) gitModalCommitsList.innerHTML = `<div style="color: var(--text-secondary); font-style: italic;">Loading history...</div>`;
    if (gitModalDiffBox) gitModalDiffBox.textContent = "Loading changes diff...";
    
    // Fetch Git Status
    fetch("/api/git/status")
    .then(r => r.json())
    .then(data => {
        if (gitModalBranch) {
            gitModalBranch.textContent = data.branch || "unknown";
        }
        
        if (gitModalStatusSummary && gitModalChangesList) {
            if (data.status_output && data.status_output.trim() !== "") {
                gitModalStatusSummary.textContent = "Modified (Pending local commits)";
                gitModalStatusSummary.style.color = "var(--warning)";
                
                gitModalChangesList.innerHTML = "";
                const lines = data.status_output.split("\n");
                lines.forEach(line => {
                    if (line.trim() === "") return;
                    const fileDiv = document.createElement("div");
                    fileDiv.textContent = line;
                    if (line.includes("modified:")) fileDiv.style.color = "var(--warning)";
                    else if (line.includes("new file:")) fileDiv.style.color = "var(--success)";
                    else if (line.includes("deleted:")) fileDiv.style.color = "var(--danger)";
                    else fileDiv.style.color = "var(--text-secondary)";
                    gitModalChangesList.appendChild(fileDiv);
                });
            } else {
                gitModalStatusSummary.textContent = "Clean (All changes committed)";
                gitModalStatusSummary.style.color = "var(--success)";
                gitModalChangesList.innerHTML = `<div style="color: var(--text-secondary); font-style: italic;">No uncommitted modifications in workspace.</div>`;
            }
        }

        // Render commits log history
        if (gitModalCommitsList) {
            if (data.commits && data.commits.length > 0) {
                gitModalCommitsList.innerHTML = "";
                data.commits.forEach(commit => {
                    const commitDiv = document.createElement("div");
                    commitDiv.style.display = "flex";
                    commitDiv.style.borderBottom = "1px solid rgba(255, 255, 255, 0.03)";
                    commitDiv.style.paddingBottom = "0.2rem";
                    
                    const parts = commit.split(" ");
                    const hash = parts[0];
                    const msg = parts.slice(1).join(" ");
                    
                    const hashSpan = document.createElement("span");
                    hashSpan.textContent = hash;
                    hashSpan.style.color = "var(--accent-cyan)";
                    hashSpan.style.fontWeight = "bold";
                    hashSpan.style.marginRight = "0.8rem";
                    
                    const msgSpan = document.createElement("span");
                    msgSpan.textContent = msg;
                    msgSpan.style.flex = "1";
                    msgSpan.style.color = "var(--text-primary)";
                    
                    const rollbackBtn = document.createElement("button");
                    rollbackBtn.className = "text-btn danger-btn-text";
                    rollbackBtn.textContent = "⏪ Rollback";
                    rollbackBtn.style.padding = "2px 6px";
                    rollbackBtn.style.fontSize = "0.72rem";
                    rollbackBtn.style.marginLeft = "0.6rem";
                    rollbackBtn.style.color = "var(--danger)";
                    rollbackBtn.style.borderColor = "rgba(239, 68, 68, 0.2)";
                    rollbackBtn.addEventListener("click", () => executeGitRollback(hash));
                    
                    commitDiv.appendChild(hashSpan);
                    commitDiv.appendChild(msgSpan);
                    commitDiv.appendChild(rollbackBtn);
                    gitModalCommitsList.appendChild(commitDiv);
                });
            } else {
                gitModalCommitsList.innerHTML = `<div style="color: var(--text-secondary); font-style: italic;">No commit history logs available yet.</div>`;
            }
        }
    })
    .catch(err => {
        console.error("Failed to load Git status in modal:", err);
        if (gitModalStatusSummary) gitModalStatusSummary.textContent = "Error checking status";
    });
    
    // Fetch Git Diff
    fetch("/api/git/diff")
    .then(r => r.json())
    .then(data => {
        if (gitModalDiffBox) {
            if (data.diff && data.diff.trim() !== "") {
                gitModalDiffBox.innerHTML = "";
                const lines = data.diff.split("\n");
                lines.forEach(line => {
                    const lineSpan = document.createElement("span");
                    lineSpan.textContent = line + "\n";
                    if (line.startsWith("+") && !line.startsWith("+++")) {
                        lineSpan.style.color = "#10b981";
                        lineSpan.style.backgroundColor = "rgba(16, 185, 129, 0.05)";
                    } else if (line.startsWith("-") && !line.startsWith("---")) {
                        lineSpan.style.color = "#ef4444";
                        lineSpan.style.backgroundColor = "rgba(239, 68, 68, 0.05)";
                    } else if (line.startsWith("@@")) {
                        lineSpan.style.color = "var(--accent-cyan)";
                    } else if (line.startsWith("diff ") || line.startsWith("index ")) {
                        lineSpan.style.color = "var(--text-secondary)";
                    }
                    gitModalDiffBox.appendChild(lineSpan);
                });
            } else {
                gitModalDiffBox.textContent = "No differences detected (Workspace matches active branch head).";
            }
        }
    })
    .catch(err => {
        console.error("Failed to load Git diff in modal:", err);
        if (gitModalDiffBox) gitModalDiffBox.textContent = "Error loading differences.";
    });
}

// Bind triggers
if (gitStatusBadge) {
    gitStatusBadge.style.cursor = "pointer";
    gitStatusBadge.title = "Open Git Version Control Center";
    gitStatusBadge.addEventListener("click", openGitCenter);
}

if (closeGitModalBtn) {
    closeGitModalBtn.addEventListener("click", () => {
        if (gitModal) gitModal.style.display = "none";
    });
}

if (gitModal) {
    gitModal.addEventListener("click", (e) => {
        if (e.target === gitModal) {
            gitModal.style.display = "none";
        }
    });
}

// Initialize Xterm.js Terminal Instance (Interactive Shell)
let term = null;
let fitAddon = null;
let fitAddonConsole = null;

if (document.getElementById("terminal-container")) {
    term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#05080f',
            foreground: '#e2e8f0',
            cursor: '#00dfd8',
            black: '#000000',
            red: '#ef4444',
            green: '#10b981',
            yellow: '#f59e0b',
            blue: '#0066ff',
            magenta: '#7000ff',
            cyan: '#00dfd8',
            white: '#ffffff'
        },
        fontSize: 12,
        fontFamily: 'Fira Code, monospace',
        convertEol: true
    });
    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById('terminal-container'));
    try { fitAddon.fit(); } catch(e) {}
    
    term.write("🐚 Live Orchestration Terminal [Active Session]\r\n");
    term.write("System ready. Enter application requirements to start compilation.\r\n\r\n");

    let currentLine = "";
    term.onData(data => {
        const code = data.charCodeAt(0);
        if (code === 13) { // Enter
            term.write("\r\n");
            fetch("/api/terminal/write", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ data: currentLine + "\r\n" })
            });
            currentLine = "";
        } else if (code === 127 || code === 8) { // Backspace
            if (currentLine.length > 0) {
                currentLine = currentLine.slice(0, -1);
                term.write("\b \b");
            }
        } else if (code < 32 && code !== 9 && code !== 3) {
            if (code === 3) { // Ctrl+C
                fetch("/api/terminal/write", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ data: "\x03" })
                });
                term.write("^C\r\n");
                currentLine = "";
            }
        } else {
            currentLine += data;
            term.write(data);
        }
    });

    setInterval(() => {
        fetch("/api/terminal/read")
        .then(r => r.json())
        .then(res => {
            if (res.data) {
                term.write(res.data);
            }
        });
    }, 100);
}

// Initialize Xterm.js Console Instance (Agent Console Logs)
let termConsole = null;
if (document.getElementById("console-logs-container")) {
    termConsole = new Terminal({
        cursorBlink: false,
        theme: {
            background: '#05080f',
            foreground: '#e2e8f0',
            cursor: 'transparent',
            black: '#000000',
            red: '#ef4444',
            green: '#10b981',
            yellow: '#f59e0b',
            blue: '#0066ff',
            magenta: '#7000ff',
            cyan: '#00dfd8',
            white: '#ffffff'
        },
        fontSize: 12,
        fontFamily: 'Fira Code, monospace',
        convertEol: true,
        readOnly: true
    });
    fitAddonConsole = new FitAddon.FitAddon();
    termConsole.loadAddon(fitAddonConsole);
    termConsole.open(document.getElementById('console-logs-container'));
    try { fitAddonConsole.fit(); } catch(e) {}
    termConsole.write("🤖 Agent Console logs will stream here in real-time when simulation runs...\r\n");
}

// Bind Terminal Tabs Triggers
const termTabShell = document.getElementById("term-tab-shell");
const termTabConsole = document.getElementById("term-tab-console");
const termContainer = document.getElementById("terminal-container");
const consoleLogsContainer = document.getElementById("console-logs-container");

function switchTerminalTab(tab) {
    if (tab === "shell") {
        if (termTabShell) {
            termTabShell.classList.add("active");
            termTabShell.style.background = "rgba(255,255,255,0.03)";
            termTabShell.style.color = "var(--accent-cyan)";
        }
        if (termTabConsole) {
            termTabConsole.classList.remove("active");
            termTabConsole.style.background = "none";
            termTabConsole.style.color = "var(--text-secondary)";
        }
        if (termContainer) termContainer.style.display = "block";
        if (consoleLogsContainer) consoleLogsContainer.style.display = "none";
        setTimeout(() => { if (fitAddon) { try { fitAddon.fit(); } catch(e) {} } }, 20);
    } else if (tab === "console") {
        if (termTabConsole) {
            termTabConsole.classList.add("active");
            termTabConsole.style.background = "rgba(255,255,255,0.03)";
            termTabConsole.style.color = "var(--accent-cyan)";
        }
        if (termTabShell) {
            termTabShell.classList.remove("active");
            termTabShell.style.background = "none";
            termTabShell.style.color = "var(--text-secondary)";
        }
        if (termContainer) termContainer.style.display = "none";
        if (consoleLogsContainer) consoleLogsContainer.style.display = "block";
        setTimeout(() => { if (fitAddonConsole) { try { fitAddonConsole.fit(); } catch(e) {} } }, 20);
    }
}

if (termTabShell) {
    termTabShell.addEventListener("click", () => switchTerminalTab("shell"));
}
if (termTabConsole) {
    termTabConsole.addEventListener("click", () => switchTerminalTab("console"));
}

window.addEventListener("resize", () => {
    if (fitAddon) { try { fitAddon.fit(); } catch(e) {} }
    if (fitAddonConsole) { try { fitAddonConsole.fit(); } catch(e) {} }
});

// ==========================================
// PREMIUM UPGRADES EVENT HANDLERS & BINDINGS
// ==========================================

// 1. Custom Agent Personas Configuration
const DEFAULT_PERSONA_PROMPTS = {
    orchestrator: "You are the central Orchestrator Supervisor. Your task is to coordinate a team of developer agents.",
    analyst: "You are an expert Business Analyst.\nAnalyze the following request and detail the user requirements, criteria, and edge cases.",
    impact: "You are a Software Architect and Impact Analyzer.\nCompare the new requirements against the existing codebase files. Determine which files are affected, what new files must be created, and any risks or dependency issues.",
    programmer: "You are a senior Software Implementation Engineer.\nYour task is to write clean, operational, and well-commented code files according to the requirements and impact plan.\nWrite the complete code for each target file. Do not use placeholders or skip details.",
    deployer: "You are a DevOps and Deployment Engineer.\nFor the application built under these requirements, write:\n1. A local deployment script:\n   - On Windows systems, write a `deploy.bat` file.\n   - For other platforms, write a `deploy.sh` script or a python script `deploy.py`.\n2. A CI/CD Pipeline configuration file:\n   - Generate an Azure DevOps pipeline config (`azure-pipelines.yml`) to support Azure DevOps/TFS.\n   - Also generate a GitHub Actions workflow (`.github/workflows/ci.yml`) to support GitHub repository pipelines.\n   - Both pipelines should be configured to install dependencies, run linting/compilation checks, execute your unit tests, and trigger static security/vulnerability scans (e.g. Bandit for Python)."
};

function loadCustomPrompts() {
    fetch("/api/settings/prompts")
    .then(r => r.json())
    .then(prompts => {
        const oInput = document.getElementById("prompt-orchestrator");
        const aInput = document.getElementById("prompt-analyst");
        const iInput = document.getElementById("prompt-impact");
        const pInput = document.getElementById("prompt-programmer");
        const dInput = document.getElementById("prompt-deployer");
        if (oInput) oInput.value = (prompts.orchestrator && prompts.orchestrator.trim()) ? prompts.orchestrator : DEFAULT_PERSONA_PROMPTS.orchestrator;
        if (aInput) aInput.value = (prompts.analyst && prompts.analyst.trim()) ? prompts.analyst : DEFAULT_PERSONA_PROMPTS.analyst;
        if (iInput) iInput.value = (prompts.impact && prompts.impact.trim()) ? prompts.impact : DEFAULT_PERSONA_PROMPTS.impact;
        if (pInput) pInput.value = (prompts.programmer && prompts.programmer.trim()) ? prompts.programmer : DEFAULT_PERSONA_PROMPTS.programmer;
        if (dInput) dInput.value = (prompts.deployer && prompts.deployer.trim()) ? prompts.deployer : DEFAULT_PERSONA_PROMPTS.deployer;
    })
    .catch(err => console.error("Failed to load prompts:", err));
}

const resetPersonasBtn = document.getElementById("reset-personas-btn");
if (resetPersonasBtn) {
    resetPersonasBtn.addEventListener("click", () => {
        const oInput = document.getElementById("prompt-orchestrator");
        const aInput = document.getElementById("prompt-analyst");
        const iInput = document.getElementById("prompt-impact");
        const pInput = document.getElementById("prompt-programmer");
        const dInput = document.getElementById("prompt-deployer");
        if (oInput) oInput.value = DEFAULT_PERSONA_PROMPTS.orchestrator;
        if (aInput) aInput.value = DEFAULT_PERSONA_PROMPTS.analyst;
        if (iInput) iInput.value = DEFAULT_PERSONA_PROMPTS.impact;
        if (pInput) pInput.value = DEFAULT_PERSONA_PROMPTS.programmer;
        if (dInput) dInput.value = DEFAULT_PERSONA_PROMPTS.deployer;
    });
}


const agentPersonasToggle = document.getElementById("agent-personas-toggle");
const agentPersonasContainer = document.getElementById("agent-personas-container");
const personasChevron = document.getElementById("personas-chevron");

if (agentPersonasToggle && agentPersonasContainer) {
    agentPersonasToggle.addEventListener("click", () => {
        const isCollapsed = agentPersonasContainer.style.display === "none";
        agentPersonasContainer.style.display = isCollapsed ? "flex" : "none";
        if (personasChevron) personasChevron.textContent = isCollapsed ? "▲" : "▼";
    });
}

// 2. SQLite Semantic Cache Inspector
const cacheInspectorToggle = document.getElementById("cache-inspector-toggle");
const cacheInspectorContainer = document.getElementById("cache-inspector-container");
const cacheChevron = document.getElementById("cache-chevron");
const cacheTableBody = document.getElementById("cache-table-body");
const clearCacheBtn = document.getElementById("clear-cache-btn");

if (cacheInspectorToggle && cacheInspectorContainer) {
    cacheInspectorToggle.addEventListener("click", () => {
        const isCollapsed = cacheInspectorContainer.style.display === "none";
        cacheInspectorContainer.style.display = isCollapsed ? "flex" : "none";
        if (cacheChevron) cacheChevron.textContent = isCollapsed ? "▲" : "▼";
        if (isCollapsed) {
            loadCacheList();
        }
    });
}

function loadCacheList() {
    if (!cacheTableBody) return;
    fetch("/api/cache/list")
    .then(r => r.json())
    .then(cacheItems => {
        cacheTableBody.innerHTML = "";
        if (cacheItems.length === 0) {
            cacheTableBody.innerHTML = `<tr><td colspan="3" style="padding: 10px; text-align: center; color: var(--text-secondary);">No semantic cache entries found.</td></tr>`;
            return;
        }
        cacheItems.forEach(item => {
            const row = document.createElement("tr");
            row.style.borderBottom = "1px solid rgba(255,255,255,0.04)";
            
            const modelCell = document.createElement("td");
            modelCell.style.padding = "6px 10px";
            modelCell.textContent = `${item.provider} (${item.model})`;
            row.appendChild(modelCell);
            
            const promptCell = document.createElement("td");
            promptCell.style.padding = "6px 10px";
            promptCell.style.maxWidth = "200px";
            promptCell.style.overflow = "hidden";
            promptCell.style.textOverflow = "ellipsis";
            promptCell.style.whiteSpace = "nowrap";
            promptCell.textContent = item.prompt;
            promptCell.title = item.prompt;
            row.appendChild(promptCell);
            
            const actionCell = document.createElement("td");
            actionCell.style.padding = "6px 10px";
            actionCell.style.textAlign = "center";
            const delBtn = document.createElement("button");
            delBtn.className = "text-btn danger-btn-text";
            delBtn.textContent = "🗑️";
            delBtn.title = "Delete Entry";
            delBtn.style.padding = "2px 4px";
            delBtn.style.fontSize = "0.72rem";
            delBtn.addEventListener("click", () => deleteCacheItem(item.id));
            actionCell.appendChild(delBtn);
            row.appendChild(actionCell);
            
            cacheTableBody.appendChild(row);
        });
    })
    .catch(err => console.error("Failed to load cache entries:", err));
}

function deleteCacheItem(itemId) {
    appConfirm(
        "Remove this entry from semantic cache?",
        () => {
            fetch(`/api/cache/delete/${itemId}`, { method: "DELETE" })
            .then(r => r.json())
            .then(() => loadCacheList())
            .catch(err => alert("Failed to delete cache item: " + err));
        },
        null,
        "Remove Entry",
        "Cancel",
        "Delete Cache Entry",
        "🗑️"
    );
}

if (clearCacheBtn) {
    clearCacheBtn.addEventListener("click", () => {
        appConfirm(
            "Are you sure you want to purge the entire semantic cache database?",
            () => {
                fetch("/api/cache/clear", { method: "POST" })
                .then(r => r.json())
                .then(() => loadCacheList())
                .catch(err => alert("Failed to clear cache: " + err));
            },
            null,
            "Purge Cache",
            "Cancel",
            "Purge Semantic Cache",
            "⚠️"
        );
    });
}

// 3. Git Branch Switching and Creation
const gitModalBranchSelect = document.getElementById("git-modal-branch-select");
const gitModalNewBranchBtn = document.getElementById("git-modal-new-branch-btn");

function loadGitBranches() {
    if (!gitModalBranchSelect) return;
    fetch("/api/git/branches")
    .then(r => r.json())
    .then(data => {
        gitModalBranchSelect.innerHTML = "";
        if (!data.branches || data.branches.length === 0) {
            const opt = document.createElement("option");
            opt.textContent = "No branches";
            gitModalBranchSelect.appendChild(opt);
            return;
        }
        data.branches.forEach(b => {
            const opt = document.createElement("option");
            opt.value = b;
            opt.textContent = b;
            if (b === data.active) {
                opt.selected = true;
            }
            gitModalBranchSelect.appendChild(opt);
        });
    })
    .catch(err => console.error("Failed to load branches:", err));
}

if (gitModalBranchSelect) {
    gitModalBranchSelect.addEventListener("change", () => {
        const branchName = gitModalBranchSelect.value;
        if (!branchName) return;
        fetch("/api/git/branch/switch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: branchName })
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail) });
            return r.json();
        })
        .then(() => {
            openFiles = {}; // Clear open file cache since we swapped branch!
            if (codeEditor) codeEditor.setValue("");
            renderTabs();
            pollStatus();
            alert(`Switched to branch: ${branchName}`);
        })
        .catch(err => {
            alert("Failed to switch branch: " + err.message);
            loadGitBranches(); // Reload correct branch highlights
        });
    });
}

if (gitModalNewBranchBtn) {
    gitModalNewBranchBtn.addEventListener("click", () => {
        const branchName = prompt("Enter name for the new branch (e.g. feature-login):");
        if (!branchName) return;
        fetch("/api/git/branch/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: branchName })
        })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw new Error(e.detail) });
            return r.json();
        })
        .then(() => {
            openFiles = {};
            if (codeEditor) codeEditor.setValue("");
            renderTabs();
            pollStatus();
            alert(`Created and checked out branch: ${branchName}`);
        })
        .catch(err => alert("Failed to create branch: " + err.message));
    });
}

// Rollback triggers hook inside populate commit logs modal
function executeGitRollback(commitHash) {
    appConfirm(
        `Are you sure you want to perform a hard rollback of all files to commit: ${commitHash}? Unsaved changes in your workspace will be lost.`,
        () => {
            fetch("/api/git/rollback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ commit: commitHash })
            })
            .then(r => {
                if (!r.ok) return r.json().then(e => { throw new Error(e.detail) });
                return r.json();
            })
            .then(() => {
                openFiles = {};
                if (codeEditor) codeEditor.setValue("");
                renderTabs();
                pollStatus();
                alert(`Successfully rolled back repository workspace to commit ${commitHash}!`);
                const gitModal = document.getElementById("git-modal");
                if (gitModal) gitModal.style.display = "none";
            })
            .catch(err => alert("Rollback failed: " + err.message));
        },
        null,
        "Rollback Workspace",
        "Cancel",
        "Perform Git Rollback",
        "⚠️"
    );
}

// 4. Fullscreen Prompt / Requirements Editor Modal
const promptModal = document.getElementById("prompt-modal");
const expandPromptBtn = document.getElementById("expand-prompt-btn");
const closePromptModal = document.getElementById("close-prompt-modal");
const cancelPromptModalBtn = document.getElementById("cancel-prompt-modal-btn");
const savePromptModalBtn = document.getElementById("save-prompt-modal-btn");
const promptModalTextarea = document.getElementById("prompt-modal-textarea");

if (expandPromptBtn && promptModal) {
    expandPromptBtn.addEventListener("click", () => {
        if (promptModalTextarea && promptInput) {
            promptModalTextarea.value = promptInput.value;
        }
        promptModal.style.display = "flex";
        setTimeout(() => { if (promptModalTextarea) promptModalTextarea.focus(); }, 50);
    });
}

const hidePromptModal = () => {
    if (promptModal) promptModal.style.display = "none";
};

if (closePromptModal) closePromptModal.addEventListener("click", hidePromptModal);
if (cancelPromptModalBtn) cancelPromptModalBtn.addEventListener("click", hidePromptModal);

if (savePromptModalBtn && promptModalTextarea && promptInput) {
    savePromptModalBtn.addEventListener("click", () => {
        promptInput.value = promptModalTextarea.value;
        hidePromptModal();
        promptInput.dispatchEvent(new Event("input"));
    });
}

// 5. Settings Left Navigation Sidebar Tab Switcher
const settingsTabBtns = document.querySelectorAll(".settings-tab-btn");
const settingsSectionContents = document.querySelectorAll(".settings-section-content");
const settingsPanelTitle = document.getElementById("settings-panel-title");

if (settingsTabBtns.length > 0) {
    settingsTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            // Remove active style classes from all buttons
            settingsTabBtns.forEach(b => {
                b.classList.remove("active");
                b.style.color = "var(--text-secondary)";
                b.style.background = "none";
                b.style.borderLeft = "none";
            });
            
            // Hide all setting sub-sections
            settingsSectionContents.forEach(sec => sec.style.display = "none");
            
            // Set active class and colors on selected tab
            btn.classList.add("active");
            btn.style.color = "var(--text-primary)";
            btn.style.background = "rgba(255, 255, 255, 0.05)";
            btn.style.borderLeft = "2px solid var(--accent-cyan)";
            
            // Display targeted section content
            const targetId = btn.getAttribute("data-target");
            const targetSec = document.getElementById(targetId);
            if (targetSec) {
                targetSec.style.display = "block";
                
                // If opening cache tab, reload records instantly
                if (targetId === "settings-sec-cache") {
                    loadCacheList();
                }
            }
            
            // Update panel header title
            if (settingsPanelTitle) {
                settingsPanelTitle.textContent = btn.textContent;
            }
        });
    });
}

// 6. Light Theme Toggle Manager
const themeToggleBtn = document.getElementById("theme-toggle-btn");

const applyTheme = (theme) => {
    if (theme === "light") {
        document.documentElement.classList.add("light-theme");
        if (themeToggleBtn) {
            themeToggleBtn.textContent = "🌙";
            themeToggleBtn.title = "Switch to Dark Theme";
        }
    } else {
        document.documentElement.classList.remove("light-theme");
        if (themeToggleBtn) {
            themeToggleBtn.textContent = "☀️";
            themeToggleBtn.title = "Switch to Light Theme";
        }
    }
};

// Check for saved theme preference or default to dark
const savedTheme = localStorage.getItem("theme") || "dark";
applyTheme(savedTheme);

if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.classList.contains("light-theme") ? "light" : "dark";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        localStorage.setItem("theme", newTheme);
        applyTheme(newTheme);
    });
}

// 7. Work Summary Modal Event Listeners
const workSummaryModal = document.getElementById("work-summary-modal");
const closeWorkSummaryModalBtn = document.getElementById("close-work-summary-modal-btn");
const okWorkSummaryModalBtn = document.getElementById("ok-work-summary-modal-btn");

const closeWorkSummaryModal = () => {
    if (workSummaryModal) {
        workSummaryModal.style.display = "none";
    }
};

if (closeWorkSummaryModalBtn) {
    closeWorkSummaryModalBtn.addEventListener("click", closeWorkSummaryModal);
}
if (okWorkSummaryModalBtn) {
    okWorkSummaryModalBtn.addEventListener("click", closeWorkSummaryModal);
}
if (workSummaryModal) {
    workSummaryModal.addEventListener("click", (e) => {
        if (e.target === workSummaryModal) {
            closeWorkSummaryModal();
        }
    });
}

// 8. LLM Observability & Cost Tracking (Telemetry) Actions
let currentTelemetryData = null;

function loadTelemetry() {
    const tableBody = document.getElementById("telemetry-table-body");
    const costBox = document.getElementById("telemetry-total-cost");
    const tokensBox = document.getElementById("telemetry-total-tokens");
    const latencyBox = document.getElementById("telemetry-avg-latency");
    const callsBox = document.getElementById("telemetry-total-calls");
    
    fetch("/api/telemetry")
    .then(r => r.json())
    .then(data => {
        currentTelemetryData = data;
        
        if (costBox) costBox.textContent = `$${data.totals.total_cost.toFixed(6)}`;
        if (tokensBox) tokensBox.textContent = data.totals.total_tokens.toLocaleString();
        if (latencyBox) latencyBox.textContent = `${data.totals.avg_latency}s`;
        if (callsBox) callsBox.textContent = data.totals.total_calls;
        
        if (!tableBody) return;
        tableBody.innerHTML = "";
        
        if ((!data.grouped_runs || data.grouped_runs.length === 0) && (!data.orphaned_logs || data.orphaned_logs.length === 0)) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-secondary);">No telemetry logs captured yet. Run a workflow to populate this dashboard!</td></tr>`;
            return;
        }
        
        // Render Grouped Runs (Requirement Runs)
        if (data.grouped_runs && data.grouped_runs.length > 0) {
            data.grouped_runs.forEach(run => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid var(--border-color)";
                tr.style.cursor = "pointer";
                tr.setAttribute("data-run-id", run.id);

                // Toggle cell
                const toggleCell = document.createElement("td");
                toggleCell.style.padding = "10px";
                toggleCell.style.textAlign = "center";
                toggleCell.style.fontSize = "0.7rem";
                toggleCell.innerHTML = `<span class="toggle-icon" style="transition: transform 0.2s ease; display: inline-block;">▶</span>`;
                tr.appendChild(toggleCell);

                // Timestamp
                const timeCell = document.createElement("td");
                timeCell.style.padding = "10px";
                timeCell.textContent = new Date(run.timestamp).toLocaleString();
                tr.appendChild(timeCell);

                // Requirement Prompt (Truncated)
                const promptCell = document.createElement("td");
                promptCell.style.padding = "10px";
                promptCell.style.maxWidth = "350px";
                promptCell.style.whiteSpace = "nowrap";
                promptCell.style.overflow = "hidden";
                promptCell.style.textOverflow = "ellipsis";
                promptCell.textContent = run.prompt;
                promptCell.title = run.prompt;
                tr.appendChild(promptCell);

                // LLM Engine/Model
                const engineCell = document.createElement("td");
                engineCell.style.padding = "10px";
                engineCell.innerHTML = `<span class="agent-badge" style="font-size: 0.72rem; color: var(--accent-cyan); font-weight: 500;">${run.provider.toUpperCase()} / ${run.model}</span>`;
                tr.appendChild(engineCell);

                // API Calls
                const callsCell = document.createElement("td");
                callsCell.style.padding = "10px";
                callsCell.style.textAlign = "center";
                callsCell.style.fontWeight = "bold";
                callsCell.textContent = run.total_calls;
                tr.appendChild(callsCell);

                // Total Tokens
                const tokensCell = document.createElement("td");
                tokensCell.style.padding = "10px";
                tokensCell.style.textAlign = "right";
                tokensCell.textContent = run.total_tokens.toLocaleString();
                tr.appendChild(tokensCell);

                // Total Cost
                const costCell = document.createElement("td");
                costCell.style.padding = "10px";
                costCell.style.textAlign = "right";
                costCell.style.fontWeight = "600";
                costCell.style.color = "var(--accent-teal)";
                costCell.textContent = `$${run.total_cost.toFixed(6)}`;
                tr.appendChild(costCell);

                tableBody.appendChild(tr);

                // Collapse Details Row
                const detailTr = document.createElement("tr");
                detailTr.className = "telemetry-detail-row";
                detailTr.style.display = "none";
                detailTr.style.background = "rgba(0,0,0,0.15)";
                
                const detailTd = document.createElement("td");
                detailTd.setAttribute("colspan", "7");
                detailTd.style.padding = "0px";
                
                const containerDiv = document.createElement("div");
                containerDiv.style.padding = "15px 20px 20px 20px";
                containerDiv.style.borderLeft = "4px solid var(--accent-purple)";
                containerDiv.style.display = "flex";
                containerDiv.style.flexDirection = "column";
                containerDiv.style.gap = "10px";

                let detailsHtml = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <h4 style="margin: 0; color: var(--accent-purple); font-size: 0.76rem; text-transform: uppercase; font-weight: 600;">Detailed Agent Call Telemetry Log</h4>
                        <span style="font-size: 0.72rem; color: var(--text-secondary);">Avg Latency: <strong>${run.avg_latency}s</strong></span>
                    </div>
                `;

                if (!run.details || run.details.length === 0) {
                    detailsHtml += `<p style="margin: 0; font-size: 0.74rem; color: var(--text-secondary); text-align: center; padding: 1rem 0;">No individual LLM calls recorded (e.g. bypassed via cached files or CLI providers).</p>`;
                } else {
                    detailsHtml += `
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.74rem; text-align: left;">
                            <thead>
                                <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); color: var(--text-secondary);">
                                    <th style="padding: 6px 8px; font-weight: 600;">Timestamp</th>
                                    <th style="padding: 6px 8px; font-weight: 600;">Agent Node</th>
                                    <th style="padding: 6px 8px; font-weight: 600;">Engine Model</th>
                                    <th style="padding: 6px 8px; font-weight: 600; text-align: right;">Tokens</th>
                                    <th style="padding: 6px 8px; font-weight: 600; text-align: right;">Latency</th>
                                    <th style="padding: 6px 8px; font-weight: 600; text-align: right;">Cost (USD)</th>
                                    <th style="padding: 6px 8px; font-weight: 600; text-align: center; width: 80px;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    run.details.forEach(detail => {
                        detailsHtml += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);" class="hover-row">
                                <td style="padding: 6px 8px;">${new Date(detail.timestamp).toLocaleTimeString()}</td>
                                <td style="padding: 6px 8px;"><span class="agent-badge" style="font-size: 0.68rem; padding: 0.1rem 0.3rem;">${detail.agent_name.toUpperCase()}</span></td>
                                <td style="padding: 6px 8px; color: var(--text-secondary);">${detail.provider} / ${detail.model}</td>
                                <td style="padding: 6px 8px; text-align: right;">${detail.total_tokens.toLocaleString()}</td>
                                <td style="padding: 6px 8px; text-align: right;">${detail.latency_sec}s</td>
                                <td style="padding: 6px 8px; text-align: right;">$${detail.cost_usd.toFixed(6)}</td>
                                <td style="padding: 6px 8px; text-align: center;">
                                    <button class="inspect-btn text-btn" data-log-json='${encodeURIComponent(JSON.stringify(detail))}' style="font-size: 0.68rem; padding: 0.1rem 0.4rem; color: var(--accent-cyan) !important; border-color: rgba(6, 182, 212, 0.25) !important;">🔍 Inspect</button>
                                </td>
                            </tr>
                        `;
                    });

                    detailsHtml += `
                            </tbody>
                        </table>
                    `;
                }

                containerDiv.innerHTML = detailsHtml;
                detailTd.appendChild(containerDiv);
                detailTr.appendChild(detailTd);
                tableBody.appendChild(detailTr);

                // Toggle click bind
                tr.addEventListener("click", (e) => {
                    if (e.target.closest(".inspect-btn")) return;
                    const isCollapsed = (detailTr.style.display === "none");
                    detailTr.style.display = isCollapsed ? "table-row" : "none";
                    const icon = toggleCell.querySelector(".toggle-icon");
                    if (icon) {
                        icon.style.transform = isCollapsed ? "rotate(90deg)" : "rotate(0deg)";
                    }
                });
            });
        }

        // Render Orphaned Logs
        if (data.orphaned_logs && data.orphaned_logs.length > 0) {
            const separatorTr = document.createElement("tr");
            separatorTr.innerHTML = `<td colspan="7" style="padding: 10px; background: rgba(255,255,255,0.03); color: var(--text-secondary); font-weight: bold; font-size: 0.72rem; letter-spacing: 0.05em; text-transform: uppercase;">Orphaned / Standalone API Calls</td>`;
            tableBody.appendChild(separatorTr);

            data.orphaned_logs.forEach(log => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid var(--border-color)";
                tr.style.cursor = "pointer";

                tr.innerHTML = `
                    <td style="padding: 10px; text-align: center;"></td>
                    <td style="padding: 10px;">${new Date(log.timestamp).toLocaleString()}</td>
                    <td style="padding: 10px; max-width: 350px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${log.prompt_text}">${log.prompt_text}</td>
                    <td style="padding: 10px;"><span class="agent-badge" style="font-size: 0.72rem; color: var(--accent-cyan);">${log.provider} / ${log.model}</span></td>
                    <td style="padding: 10px; text-align: center;">1</td>
                    <td style="padding: 10px; text-align: right;">${log.total_tokens.toLocaleString()}</td>
                    <td style="padding: 10px; text-align: right; font-weight: 600; color: var(--accent-teal);">$${log.cost_usd.toFixed(6)}</td>
                `;

                tr.addEventListener("click", () => {
                    showTelemetryDetailDrawer(log);
                });
                tableBody.appendChild(tr);
            });
        }

        // Bind inspect button listeners
        document.querySelectorAll(".inspect-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const logDataStr = decodeURIComponent(btn.getAttribute("data-log-json"));
                const log = JSON.parse(logDataStr);
                showTelemetryDetailDrawer(log);
            });
        });
    })
    .catch(err => console.error("Failed to load telemetry logs: ", err));
}

function showTelemetryDetailDrawer(log) {
    const drawer = document.getElementById("telemetry-drawer");
    const drawerAgent = document.getElementById("telemetry-drawer-agent");
    const drawerModel = document.getElementById("telemetry-drawer-model");
    const drawerPrompt = document.getElementById("telemetry-drawer-prompt");
    const drawerResponse = document.getElementById("telemetry-drawer-response");
    
    if (drawerAgent) drawerAgent.textContent = `${log.agent_name.toUpperCase()} NODE CALL`;
    if (drawerModel) drawerModel.textContent = `${log.provider.toUpperCase()} / ${log.model}`;
    if (drawerPrompt) drawerPrompt.textContent = log.prompt_text;
    if (drawerResponse) drawerResponse.textContent = log.response_text;
    
    if (drawer) {
        drawer.style.display = "flex";
        setTimeout(() => drawer.classList.add("show"), 10);
    }
}

const closeTelemetryDrawerBtn = document.getElementById("close-telemetry-drawer-btn");
const telemetryDrawer = document.getElementById("telemetry-drawer");

if (closeTelemetryDrawerBtn && telemetryDrawer) {
    closeTelemetryDrawerBtn.addEventListener("click", () => {
        telemetryDrawer.classList.remove("show");
        setTimeout(() => { telemetryDrawer.style.display = "none"; }, 300);
    });
}

const resetTelemetryBtn = document.getElementById("reset-telemetry-btn");
const telemetryResetModal = document.getElementById("telemetry-reset-modal");
const cancelTelemetryResetBtn = document.getElementById("cancel-telemetry-reset-btn");
const confirmTelemetryResetBtn = document.getElementById("confirm-telemetry-reset-btn");

if (resetTelemetryBtn && telemetryResetModal) {
    resetTelemetryBtn.addEventListener("click", () => {
        telemetryResetModal.style.display = "flex";
    });
}

if (cancelTelemetryResetBtn && telemetryResetModal) {
    cancelTelemetryResetBtn.addEventListener("click", () => {
        telemetryResetModal.style.display = "none";
    });
    telemetryResetModal.addEventListener("click", (e) => {
        if (e.target === telemetryResetModal) {
            telemetryResetModal.style.display = "none";
        }
    });
}

if (confirmTelemetryResetBtn && telemetryResetModal) {
    confirmTelemetryResetBtn.addEventListener("click", () => {
        fetch("/api/telemetry/reset", { method: "POST" })
        .then(r => r.json())
        .then(() => {
            loadTelemetry();
            telemetryResetModal.style.display = "none";
            if (telemetryDrawer) {
                telemetryDrawer.classList.remove("show");
                setTimeout(() => { telemetryDrawer.style.display = "none"; }, 300);
            }
        })
        .catch(err => console.error("Failed to reset telemetry: ", err));
    });
}

setInterval(() => {
    const viewTelemetry = document.getElementById("view-telemetry");
    if (viewTelemetry && viewTelemetry.classList.contains("active")) {
        loadTelemetry();
    }
}, 3000);

// 9. Start Fresh "New Create" & File Delete Modal triggers
const newCreateBtn = document.getElementById("new-create-btn");
if (newCreateBtn) {
    newCreateBtn.addEventListener("click", () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Please specify application requirements first!");
            return;
        }
        
        newCreateBtn.disabled = true;
        const originalText = newCreateBtn.innerHTML;
        newCreateBtn.innerHTML = '<span class="btn-spinner"></span> Starting fresh...';
        
        triggerAgentRun(prompt, true);
        
        setTimeout(() => {
            newCreateBtn.disabled = false;
            newCreateBtn.innerHTML = originalText;
        }, 3000);
    });
}

let fileToDelete = null;

function showFileDeleteConfirmation(path) {
    fileToDelete = path;
    const modal = document.getElementById("file-delete-modal");
    const nameSpan = document.getElementById("delete-file-name");
    
    if (nameSpan) {
        nameSpan.textContent = path.split(/[\\/]/).pop();
        nameSpan.title = path;
    }
    
    if (modal) {
        modal.style.display = "flex";
    }
}

const cancelFileDeleteBtn = document.getElementById("cancel-file-delete-btn");
const confirmFileDeleteBtn = document.getElementById("confirm-file-delete-btn");
const fileDeleteModal = document.getElementById("file-delete-modal");

if (cancelFileDeleteBtn && fileDeleteModal) {
    cancelFileDeleteBtn.addEventListener("click", () => {
        fileDeleteModal.style.display = "none";
        fileToDelete = null;
    });
    fileDeleteModal.addEventListener("click", (e) => {
        if (e.target === fileDeleteModal) {
            fileDeleteModal.style.display = "none";
            fileToDelete = null;
        }
    });
}

if (confirmFileDeleteBtn && fileDeleteModal) {
    confirmFileDeleteBtn.addEventListener("click", () => {
        if (fileToDelete) {
            deleteFile(fileToDelete);
            fileDeleteModal.style.display = "none";
            fileToDelete = null;
        }
    });
}

// ==========================================
// SYSTEM DIALOG MODAL (Alert & Confirm Replacements)
// ==========================================
let currentDialogConfirmCallback = null;
let currentDialogCancelCallback = null;

function showSystemDialog({ title = "Notification", message = "", icon = "🔔", showCancel = false, confirmText = "OK", cancelText = "Cancel", onConfirm = null, onCancel = null }) {
    const modal = document.getElementById("system-dialog-modal");
    const iconEl = document.getElementById("system-dialog-icon");
    const titleEl = document.getElementById("system-dialog-title");
    const msgEl = document.getElementById("system-dialog-message");
    const cancelBtn = document.getElementById("system-dialog-cancel-btn");
    const confirmBtn = document.getElementById("system-dialog-confirm-btn");
    
    if (!modal) return;
    
    if (iconEl) iconEl.textContent = icon;
    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;
    
    if (confirmBtn) {
        confirmBtn.textContent = confirmText;
        if (confirmText.toLowerCase().includes("delete") || confirmText.toLowerCase().includes("discard") || confirmText.toLowerCase().includes("rollback") || confirmText.toLowerCase().includes("clear") || confirmText.toLowerCase().includes("purge") || confirmText.toLowerCase().includes("reset")) {
            confirmBtn.style.backgroundColor = "var(--danger)";
            confirmBtn.style.borderColor = "var(--danger)";
            confirmBtn.style.color = "#fff";
        } else {
            confirmBtn.style.backgroundColor = "";
            confirmBtn.style.borderColor = "";
            confirmBtn.style.color = "";
        }
    }
    
    if (cancelBtn) {
        cancelBtn.textContent = cancelText;
        cancelBtn.style.display = showCancel ? "inline-flex" : "none";
    }
    
    currentDialogConfirmCallback = onConfirm;
    currentDialogCancelCallback = onCancel;
    
    modal.style.display = "flex";
}

// Bind System Dialog Modal Buttons
const sysDialogConfirmBtn = document.getElementById("system-dialog-confirm-btn");
const sysDialogCancelBtn = document.getElementById("system-dialog-cancel-btn");
const sysDialogModal = document.getElementById("system-dialog-modal");

if (sysDialogConfirmBtn) {
    sysDialogConfirmBtn.addEventListener("click", () => {
        if (sysDialogModal) sysDialogModal.style.display = "none";
        if (currentDialogConfirmCallback) {
            currentDialogConfirmCallback();
        }
        currentDialogConfirmCallback = null;
        currentDialogCancelCallback = null;
    });
}

if (sysDialogCancelBtn) {
    sysDialogCancelBtn.addEventListener("click", () => {
        if (sysDialogModal) sysDialogModal.style.display = "none";
        if (currentDialogCancelCallback) {
            currentDialogCancelCallback();
        }
        currentDialogConfirmCallback = null;
        currentDialogCancelCallback = null;
    });
}

if (sysDialogModal) {
    sysDialogModal.addEventListener("click", (e) => {
        if (e.target === sysDialogModal) {
            sysDialogModal.style.display = "none";
            if (currentDialogCancelCallback) {
                currentDialogCancelCallback();
            }
            currentDialogConfirmCallback = null;
            currentDialogCancelCallback = null;
        }
    });
}

// Global short-hands
function appAlert(message, title = "Developer Studio Alert", icon = "⚠️") {
    showSystemDialog({
        title: title,
        message: message,
        icon: icon,
        showCancel: false,
        confirmText: "OK"
    });
}

function appConfirm(message, onConfirm, onCancel = null, confirmText = "Confirm", cancelText = "Cancel", title = "Confirmation Requested", icon = "❓") {
    showSystemDialog({
        title: title,
        message: message,
        icon: icon,
        showCancel: true,
        confirmText: confirmText,
        cancelText: cancelText,
        onConfirm: onConfirm,
        onCancel: onCancel
    });
}

// Override window.alert to automatically use our premium modal layout!
window.alert = function(message) {
    appAlert(message);
};




