<div align="center">
  <img src="./Assets/Switchback logo with text of switchback.png" alt="Switchback Logo" width="200"/>
  <h1>Switchback</h1>
  <p><strong>A Deterministic, AI-Powered Career Navigator & Skill Gap Analyzer</strong></p>

  <p>
    <a href="#the-problem">The Problem</a> •
    <a href="#our-solution">Our Solution</a> •
    <a href="#key-features">Key Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#getting-started">Getting Started</a>
  </p>
</div>

---

## 🛑 The Problem

The modern tech landscape evolves incredibly fast. Professionals trying to transition to new roles or maximize their earning potential often hit a wall:
- **Generic Advice**: Most platforms offer generic, one-size-fits-all roadmaps.
- **LLM Hallucinations**: Generative AI tools frequently invent fake certifications, recommend outdated courses, or hallucinate salary impacts.
- **Decision Paralysis**: With thousands of available skills, learners don't know *which* specific skill yields the highest ROI for their time.

## 💡 Our Solution

**Switchback** is an intelligent career transition engine built on a fundamentally different philosophy: **Deterministic Data over Generative Guesses.**

Instead of relying on an LLM to invent your career path, Switchback uses **Dijkstra’s Algorithm** across a proprietary, pre-computed graph of over 21,000 skill relationships. It calculates the mathematically shortest, cheapest, and most efficient path from your *current* skills to your *target* role. 

Every recommendation is grounded in real job-market data, and an integrated **Machine Learning Salary Engine** predicts exactly how much each new skill will increase your earning potential in real-time.

---

## ✨ Key Features

### 🗺️ Deterministic Path Generation
No hallucinations. Switchback maps your current skills against a massive market ontology and generates a step-by-step milestone path using graph-traversal algorithms.

### 📈 ML-Powered Salary Predictions
We don't guess your salary. A highly trained **Gradient Boosting Regressor** evaluates your exact skill vector to predict your Lakhs Per Annum (LPA) trajectory. We use **SHAP (SHapley Additive exPlanations)** to explain exactly *why* a specific skill increases your worth.

### 🤖 Grounded Conversational AI
Interact naturally with our AI assistant. Powered by OpenAI, the assistant strictly acts as a conversational routing layer—it securely queries our deterministic engine to answer your questions with mathematical facts, ensuring 100% accuracy.

### 🎛️ Interactive "What-If" Simulator
Curious about a different path? The interactive timeline simulator lets you inject new skills into your profile on the fly, instantly recalculating your career trajectory, time saved, and salary jumps.

### 🎓 Smart Resource Aggregation
Every milestone comes with actionable learning resources. Switchback automatically fetches high-quality, free **YouTube** video tutorials and premium courses, caching them in MongoDB for blazing-fast retrieval.

---

## 🏗️ Technical Architecture

Switchback is a highly optimized, full-stack application designed for speed and accuracy.

| Layer | Technology Stack | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS | Delivers a deeply interactive, glassmorphism-inspired UI with smooth micro-animations. |
| **Backend** | Python 3.11, FastAPI | Handles complex graph traversal, conversational routing, and ML model inference. |
| **Database** | MongoDB | Stores the career ontology, user sessions, and API caching layers. |
| **Machine Learning** | `scikit-learn`, SHAP | Powers the dynamic salary predictor and feature importance explanations. |
| **Integrations** | YouTube Data API, Adzuna API, OpenAI | Enriches the user experience with real-world videos, jobs, and natural language understanding. |

---

## 🚀 Getting Started

Want to run Switchback locally? We've made it incredibly simple. 

Please refer to our comprehensive **[SETUP.md](./SETUP.md)** for detailed, step-by-step instructions on setting up your Python virtual environment, configuring your API keys, and launching the development servers.

---

<div align="center">
  <i>Built to navigate the complexities of the modern career landscape.</i>
</div>
