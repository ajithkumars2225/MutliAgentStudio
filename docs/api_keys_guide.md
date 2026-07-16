# Step-by-Step Guide: Creating API Keys for LLM Providers

This guide provides step-by-step instructions on how to create, retrieve, and configure API keys for all 13 supported LLM providers in the Multi-Agent Developer Studio.

---

## 🎁 Overview: Providers with Free Tiers & Free Credits (No Payment Required)

If you want to run the studio without entering any credit card or payment information, these providers offer completely free tiers or trial credits:

| Provider | Free Tier / Credit Offer | Key Features |
| :--- | :--- | :--- |
| **Ollama (Local)** | **100% Free & Unlimited** | Runs models locally on your own computer (CPU/GPU). No internet or keys required. |
| **Google Gemini** | **Free Tier** | Free access to Gemini 2.5 Flash and Flash-8B via Google AI Studio (rate-limited). |
| **OpenRouter AI** | **Free Models** | Access to several free models (e.g., Llama 3.3 70B Free, Qwen 2, Mistral) at $0 cost. |
| **Groq** | **Free Beta Access** | Extremely fast, free access to Llama 3.3 70B, Gemma 2, and Mixtral. |
| **Together AI** | **$25 Free Credits** | Gives $25 of starting credit on registration without requiring a credit card. |
| **Cohere** | **Free Trial Key** | Unlimited free development keys for building prototypes and testing models. |
| **Z.ai (Zhipu GLM)** | **Free Trial Credits** | Initial free token quota granted upon registering on the open platform. |

---

## 1. Google Gemini (Google AI Studio)
1. Go to the [Google AI Studio Console](https://aistudio.google.com/).
2. Log in with your Google account.
3. Click the **Get API key** button in the top left sidebar.
4. Click **Create API key**.
5. Select a project (or choose "Create API key in new project").
6. Copy the key (starts with `AIzaSy...`) and paste it into the **Gemini API Key** field in settings.

---

## 2. OpenAI
1. Go to the [OpenAI Developer Platform](https://platform.openai.com/).
2. Log in or create an OpenAI developer account.
3. In the left-hand sidebar, navigate to **Dashboard** $\rightarrow$ **API Keys**.
4. Click **+ Create new secret key**.
5. Give your key a name (e.g. *Developer Studio*), set permissions, and click **Create secret key**.
6. Copy the key (starts with `sk-...`) immediately, as it will not be shown again.

---

## 3. Anthropic Claude (Anthropic Console)
1. Go to the [Anthropic Console](https://console.anthropic.com/).
2. Log in or sign up for an Anthropic Developer account.
3. Click on the **API Keys** tab in the top navigation/sidebar menu.
4. Click **Create Key**.
5. Give your key a name and click **Create key**.
6. Copy the key (starts with `sk-ant-...`) and store it securely.

---

## 4. OpenRouter AI
1. Go to the [OpenRouter Dashboard](https://openrouter.ai/).
2. Create an account or log in.
3. In the top-right user menu, click on **Keys** (or navigate directly to [openrouter.ai/keys](https://openrouter.ai/keys)).
4. Click **Create Key**.
5. Give your key a name and click **Create**.
6. Copy the key (starts with `sk-or-v1-...`).

---

## 5. Groq
1. Go to the [Groq Console](https://console.groq.com/).
2. Sign up or log in.
3. Click on **API Keys** in the left sidebar menu.
4. Click **Create API Key**.
5. Name your key and click **Submit**.
6. Copy the generated key (starts with `gsk_...`).

---

## 6. DeepSeek (Official API)
1. Go to the [DeepSeek Platform Console](https://platform.deepseek.com/).
2. Sign up and verify your mobile number or email.
3. Select **API Keys** in the left sidebar menu.
4. Click **Create API Key**.
5. Name your key and click **Create**.
6. Copy the key (starts with `sk-...`).

---

## 7. Together AI
1. Go to the [Together AI Console](https://api.together.ai/).
2. Sign up (Together AI usually credits $25 of free credit upon registration).
3. Navigate to **API Keys** under the **Settings** sidebar tab.
4. Click **Create New Key** (or copy your default API key).
5. Copy the key.

---

## 8. Mistral AI (La Plateforme)
1. Go to the [Mistral AI Console](https://console.mistral.ai/).
2. Sign up or sign in.
3. Click on the **API Keys** tab in the left sidebar menu.
4. Click **Create new key**.
5. Specify a name and copy the secret key.

---

## 9. Cohere
1. Go to the [Cohere Dashboard](https://dashboard.cohere.com/).
2. Log in or register.
3. In the left navigation bar, click on **API Keys**.
4. You will see your default **Trial API Key**. You can copy it directly or click **Create API Key** for a production key.
5. Copy the key.

---

## 10. xAI (Grok)
1. Go to the [xAI Console](https://console.x.ai/).
2. Sign in using your X (formerly Twitter) account or create an xAI profile.
3. Click on **API Keys** in the navigation menu.
4. Click **Create API Key**.
5. Copy the generated key (starts with `xai-...`).

---

## 11. Z.ai (Zhipu AI GLM)
1. Go to the [Z.ai Developer Platform](https://z.ai) (or [bigmodel.cn](https://open.bigmodel.cn/)).
2. Sign up for an account.
3. Go to the **API Keys** management dashboard page.
4. Click **Create API Key** (or copy your active default key).
5. Copy the key.

---

## 12. Azure OpenAI
1. Log in to the [Azure Portal](https://portal.azure.com/).
2. Search for and select **Cognitive Services** or **Azure OpenAI**.
3. Select your Azure OpenAI resource.
4. In the left menu under *Resource Management*, click **Keys and Endpoint**.
5. Copy **KEY 1** (or KEY 2).
6. Copy the **Endpoint URL** (needed in the Base URL field).
7. Go to **Model Deployments** (Azure AI Studio) to get your deployment name (needed in the Model field).

---

## 13. AWS Bedrock
1. Log in to the [AWS Management Console](https://aws.amazon.com/).
2. Search for **Amazon Bedrock**.
3. Under **Model access** in the left sidebar, request access to the models you want to use (e.g. Claude 3.5 Sonnet, Llama 3.1).
4. Configure your AWS credentials locally on your Windows machine:
   * Install the AWS CLI and run `aws configure`.
   * Set your `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in your environment or Windows User Environment Variables.
5. In the settings panel, input your AWS region (e.g. `us-east-1`) into the Base URL box.
