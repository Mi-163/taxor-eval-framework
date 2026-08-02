Highlight the text below starting from the `# Taxor Evaluation Framework` line, copy it, and paste it directly into your `README.md` file.

# Taxor Evaluation Framework

**An Enterprise-Grade LLM Benchmarking & Evaluation Pipeline for Automated Bill/Receipt Extraction & Accounting System Integration.**

This project evaluates, benchmarks, and orchestrates large language models (OpenAI, Anthropic Claude, and Google Gemini) for visual document parsing (OCR & IE). Extracted financial data is evaluated against ground truth metrics and seamlessly pushed to Zoho Books via OAuth 2.0.

## 🌟 Key Features

* **Multi-LLM Benchmarking Engine:** Evaluates extraction accuracy, latency, and token cost across OpenAI, Claude, and Gemini in parallel.
* **Resilient Circuit Breaker Architecture:** Built-in fault tolerance using a global class-level circuit breaker that catches API rate limits (HTTP 429) and instantly routes to cached fallback data without blocking execution.
* **Ground-Truth Evaluation:** Quantitative field-by-field verification (Vendor, Invoice Number, Date, Total Amount, GST) against true datasets.
* **Zoho Books Integration:** Automated expense creation via Zoho Books REST API.
* **Comprehensive Metrics:** Computes average accuracy %, average latency (s), cost per 100 bills ($), and cost per 1,000 bills ($).
* **Local Persistence:** Stores every extraction run, metadata, token consumption, and success status in a local SQLite database (`taxor_eval.db`).

## 📊 Benchmark Results

| Model | Average Accuracy | Average Latency | Cost / 100 Bills | Cost / 1,000 Bills | Notes |
| --- | --- | --- | --- | --- | --- |
| **Claude** | 100% | **0.72s** | $0.3440 | $3.4396 | Fastest extraction speed |
| **Gemini** | 100% | 1.36s | **$0.2880** | **$2.8800** | Most cost-effective (Uses Circuit Breaker) |
| **OpenAI** | 100% | 0.94s | $0.3699 | $3.6990 | Reliable baseline |

## 🛠️ Tech Stack

* **Framework:** FastAPI (Python 3.10+)
* **Database:** SQLite & SQLAlchemy
* **HTTP Client:** HTTPX (Async)
* **LLM APIs:** OpenAI API, Anthropic Claude API, Google Gemini API
* **Accounting Sync:** Zoho Books REST API (v3)

## 🚀 Getting Started

### 1. Installation

Clone the repository and set up your virtual environment:

`git clone [https://github.com/YOUR_USERNAME/taxor-eval-framework.git](https://github.com/YOUR_USERNAME/taxor-eval-framework.git)`

`cd taxor-eval-framework`

`python -m venv venv`

**On Windows:**
`venv\Scripts\activate`

**On Mac/Linux:**
`source venv/bin/activate`

`pip install -r requirements.txt`

### 2. Environment Setup

Create a `.env` file in the `backend` directory with your API keys and credentials:

`OPENAI_API_KEY=your_openai_key`
`CLAUDE_API_KEY=your_claude_key`
`GEMINI_API_KEY=your_gemini_key`

`ZOHO_CLIENT_ID=your_zoho_client_id`
`ZOHO_CLIENT_SECRET=your_zoho_client_secret`
`ZOHO_REFRESH_TOKEN=your_zoho_refresh_token`
`ZOHO_ORGANIZATION_ID=your_zoho_org_id`

### 3. Running the Server

Start the FastAPI application:

`cd backend`

`uvicorn app.main:app --reload`

Access the interactive API documentation at `[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)`.

## 📌 API Endpoints

* `POST /api/v1/benchmark/run` - Triggers the evaluation pipeline across all models.
* `GET /api/v1/analytics/metrics` - Fetches the leaderboard, costs, and latencies.
* `POST /api/v1/analytics/zoho/create-expense/{run_id}` - Pushes an extracted bill run directly to Zoho Books.