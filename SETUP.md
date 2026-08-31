# Detailed Local Setup Guide

Welcome to Switchback! Follow these precise steps to get the frontend and backend running locally on your machine.

---

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.11+**
- **Node.js (v18+)** and **npm**
- **MongoDB**: You must have a MongoDB server running locally (usually on `mongodb://localhost:27017`) or a remote MongoDB Atlas URI.

---

## 2. Backend Setup

The backend is built with FastAPI and requires Python packages listed in `requirements.txt`.

### Step 2.1: Navigate to the Backend Directory
Open your terminal and navigate to the project root, then into the backend folder:
```bash
cd backend
```

### Step 2.2: Create a Virtual Environment
It is highly recommended to isolate your Python dependencies:
```bash
# On Windows
python -m venv .venv

# On macOS/Linux
python3 -m venv .venv
```

### Step 2.3: Activate the Virtual Environment
```bash
# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### Step 2.4: Install Requirements
With the virtual environment activated, install the backend dependencies:
```bash
pip install -r requirements.txt
```

---

## 3. Environment Variables (.env)

The project requires a `.env` file at the root of the project to configure API keys and the database connection.

1. Navigate to the project root:
   ```bash
   cd ..
   ```
2. Copy the template:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` in a text editor and fill in the values:
   - `MONGODB_URI`: Set to your MongoDB connection string (e.g., `mongodb://localhost:27017/` for local, or your Atlas URL).
   - `OPENAI_API_KEY`: Add your OpenAI key to enable the conversational assistant.
   - `YOUTUBE_API_KEY`: (Optional) Add to fetch real-time YouTube video recommendations. If omitted, a scraper fallback will be used.
   - `ADZUNA_APP_ID` & `ADZUNA_APP_KEY`: (Optional) Add to enable live job postings.

---

## 4. Frontend Setup

The frontend is built with React and Vite.

### Step 4.1: Install Node Modules
Navigate to the project root (if not already there), and install frontend dependencies:
```bash
npm --prefix frontend install
```

### Step 4.2: Frontend Environment Variables
Copy the frontend environment template:
```bash
cp frontend/.env.example frontend/.env
```
*(No modifications are typically needed here for a default local setup, as it points to `http://localhost:8011` by default).*

---

## 5. Running the Application

You need two separate terminal windows (or tabs) to run both servers concurrently.

### Terminal 1: Start the Backend
Make sure your Python virtual environment is activated, then run:
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload
```
*(The backend will start on `http://127.0.0.1:8011`)*

### Terminal 2: Start the Frontend
From the project root, run:
```bash
npm --prefix frontend run dev
```
*(The frontend will start on `http://localhost:5173`)*

---

## 6. Verification

To verify that the backend is working correctly, you can hit the health check endpoint:
```bash
curl http://127.0.0.1:8011/health
```
You should receive a JSON response indicating `"status": "healthy"`.

You can now open `http://localhost:5173` in your browser and use Switchback!
