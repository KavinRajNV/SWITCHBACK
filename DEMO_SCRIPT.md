# Switchback — Judge Presentation Demo Script & Talking Points

> **Product Differentiator**: A deterministic, data-grounded engine — every recommendation, profile extraction, and SHAP explanation traces to a real dataset, a trained model, or a graph computation. The conversational layer adds a lightweight LLM only to route questions and phrase replies; it is never a source of facts.

---

## ⏱️ Recommended Walkthrough Sequence (5-Minute Presentation)

### 1. Landing Page & Grounded-Engine Hook (1 Minute)
- **Visual**: Start at `/`. Point out the signature interactive mountain scroll-trail line with the 5-frame runner sprite.
- **Talking Points**:
  - *"Welcome to Switchback. Where a pure-LLM assistant would invent generic, unverified learning paths, every number Switchback shows you traces back to a real dataset, a trained model, or a graph computation. The conversational layer only routes your question and phrases the reply."*
  - *"The core engine is built on cleaned MongoDB collections, a 21,000-edge directed skill graph, and a 323-feature GradientBoosting salary model trained on real disclosures."*

---

### 2. Multi-Modal Profile Initialization (`/start` & `/skills`) (1 Minute)
- **Action**: Click **"Get Started"** $\to$ Select **"Enter Skills Manually"** or **"Upload Resume"**.
- **Action**: Enter `Python, SQL, Machine Learning, Statistical Analysis`. Click **"Verify via GitHub"** and type `torvalds`.
- **Talking Points**:
  - *"Learners initialize their baseline skills via layout-aware PDF sectioning, manual search autocomplete, or free-text goal prompts."*
  - *"Notice the trail-difficulty marks: green circles for beginner skills, blue squares for intermediate elevation, and black squares for expert summit skills."*
  - *"When we click 'Verify via GitHub', our backend calls the live GitHub REST API to scan repository language distributions, assigning verified skills a Tier-9 confidence score with a wax-seal badge."*

---

### 3. Target Role & Grounded Road-to-Job Trail (`/target-role`) (1 Minute)
- **Action**: Search and select **"Data Scientists"** (SOC `15-2051.00`).
- **Talking Points**:
  - *"We query our 1,016 O*NET occupation catalog. When 'Data Scientists' is selected, our Dijkstra minimum-cost graph algorithm computes the optimal skill acquisition path."*
  - *"Notice the Road-to-Job trail visualization: the number of segment posts strictly equals the real computed path length—in this case, 8 milestone steps. Hovering over any post displays its exact skill, cost weight, and graph reachability link."*

---

### 4. Learning Path, Custom Elevation Chart & What-If Simulator (`/path` & `/dashboard`) (1 Minute)
- **Action**: Click **"See My Path"** $\to$ View SVG Salary Elevation Curve. Toggle **Free / Paid** course filter. Click **"Dashboard"**.
- **Action**: In the **What-If Scenario Simulator**, click **"+ What if I know AWS?"**.
- **Talking Points**:
  - *"On the Learning Path screen, our custom SVG elevation chart plots cumulative predicted salary growth in LPA across every step, backed by SHAP explainability."*
  - *"Learners can filter between free gate courses and paid certified booklet offerings instantly."*
  - *"On the Learner Dashboard, the elevation chart splits into a solid line for achieved progress versus a dashed line for projected steps. Using the What-If simulator, toggling 'AWS' debounces a fast 300ms backend call to recompute the graph, showing that knowing AWS saves 1 full milestone!"*

---

### 5. Milestone Completion & Celebration Stretch Goals (`/celebration`) (1 Minute)
- **Action**: Click **"Mark 'Power BI' Complete"** $\to$ Select evidence tier $\to$ Navigate to `/celebration`.
- **Talking Points**:
  - *"As learners log completion evidence (self-report, project logs, or GitHub verification), Switchback recomputes the Dijkstra fringe in real time, saving redundant milestones."*
  - *"Upon reaching 100% full qualification, the Celebration screen surfaces 2-3 real O*NET primary-short related occupations—like Statisticians and Financial Quantitative Analysts—as next stretch goals, sourced directly from real taxonomy data."*

---

## 🎯 Key Questions & Judge Objections Cheat-Sheet

| Potential Objection / Question | Grounded Technical Answer |
|---|---|
| *"How does the assistant avoid hallucinating skills or courses?"* | The LLM only classifies the question's intent (and only when the keyword classifier is unsure). The answer itself is produced by one of 8 deterministic functions reading the model, graph, and database — so every skill, course, and salary figure is real. Resume parsing is fully deterministic: layout-aware PDF font-coordinate extraction + string-distance taxonomy matching. |
| *"How is salary trajectory calculated?"* | A `GradientBoostingRegressor` trained on job posting salary disclosures using 323 one-hot encoded skill features + seniority + company tiers. |
| *"How is path sequencing computed?"* | A directed graph (`NetworkX`) with 1,281 nodes and 21,137 edges built from ESCO and O*NET relations. Path generation finds the shortest path through missing required skills using Dijkstra's algorithm. |
| *"What happens if Adzuna is offline?"* | Our backend catches `httpx.ConnectTimeout` and gracefully returns `status: "unavailable"` with `jobs: []`, rendering a clean fallback banner without crashing page layout. |
