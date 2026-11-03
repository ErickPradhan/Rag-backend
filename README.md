# Palm Mind RAG Backend

A FastAPI backend with two REST APIs:

1. **Document Ingestion API** - upload a `.pdf` or `.txt`, extract the text, split it into chunks (two selectable strategies), turn the chunks into embeddings, store them in **Qdrant**, and save file metadata in an **SQL database (SQLite)**.
2. **Conversational RAG API** - a custom retrieval pipeline (no `RetrievalQAChain`), **Redis** chat memory, multi-turn questions, and **interview booking** (name, email, date, time) handled by the LLM. Bookings are stored in SQL.

No FAISS, no Chroma, no UI.

**Demo video:** https://drive.google.com/drive/folders/1yQlQKQhcExe8A00pcxaIQTY4OP6J2Gnr?usp=drive_link

---

## Quick overview of how it works

```
Upload a file --> extract text --> chunk --> embed --> Qdrant (vectors) + SQL (metadata)

Chat message --> Redis (load recent chat) --> LLM decides: question or booking?
   question --> search Qdrant --> LLM answers using only the found text
   booking  --> collect name/email/date/time over several messages --> save in SQL
```

---

## What you need before starting

| Need | Where to get it | Cost |
|---|---|---|
| Python 3.10 or newer | https://www.python.org/downloads/ (tick **"Add python.exe to PATH"** when installing) | Free |
| A Gemini API key | https://aistudio.google.com/apikey -> **Create API key** | Free |
| A Redis database (chat memory) | **Option A: Upstash** (no install) or **Option B: Docker** - see Step 4 | Free |

Qdrant needs **no setup**. By default it saves vectors in a local folder called `qdrant_data`.

---

## Setup, step by step

### Step 1 - Open the project folder
Open the folder that contains `requirements.txt` and the `app` folder in a terminal (in VS Code: **File -> Open Folder**, then **Terminal -> New Terminal**).

### Step 2 - Create a virtual environment

Windows (PowerShell):
```
py -m venv .venv
.venv\Scripts\activate
```
Mac / Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```
After this, your terminal line should start with `(.venv)`.

> Windows: if you see "running scripts is disabled", run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and activate again.

### Step 3 - Install the packages
```
python -m pip install -r requirements.txt
```

### Step 4 - Get a Redis database (choose ONE option)

**Option A - Upstash (free, hosted online, nothing to install)**
1. Go to https://upstash.com and sign up.
2. Click **Create Database** under **Redis**. Any name, any nearby region, **Free** plan, then **Create**.
3. On the database page, open the **TCP** tab (not REST).
4. Copy the link that starts with `redis://` and change the start to **`rediss://`** (one extra `s`). It looks like:
   ```
   rediss://default:YOUR_PASSWORD@your-name.upstash.io:6379
   ```
   Keep this for Step 5.

**Option B - Docker (runs Redis on your own computer)**
1. Install and start Docker Desktop.
2. In the project folder run:
   ```
   docker compose up -d
   ```
3. You don't need to change anything: the default `REDIS_URL=redis://localhost:6379/0` already matches.

### Step 5 - Create your settings file
Copy the example file to a new file called `.env`:
```
cp .env.example .env
```
(Windows PowerShell understands `cp`. In Command Prompt use `copy .env.example .env`.)

Open `.env` and change:
- `LLM_API_KEY=` -> paste your Gemini key (no spaces, no quotes).
- `REDIS_URL=` -> paste your `rediss://...` link from Upstash (skip this if you used Docker).

Save the file. **Never share or upload `.env`** - it is already listed in `.gitignore`.

### Step 6 - Start the server
```
uvicorn app.main:app --reload
```
Wait until you see `Application startup complete`. Leave this terminal open.

> The terminal prints `http://127.0.0.1:8000`. Opening it takes you straight to the
> test page. If you ever see "Not Found", add `/docs` to the end of the address:
> http://127.0.0.1:8000/docs

---

## How to test it (no coding needed)

FastAPI gives us a ready-made test page. There is no custom UI.

1. Open **http://127.0.0.1:8000/docs** in your browser.
2. You will see green and blue bars for each API. **Click a bar to open it -> click "Try it out" -> fill in the boxes -> click the blue "Execute" button -> read the result under "Server response".**

### Test 1 - Upload a document (Document Ingestion API)
1. Click **POST /documents/ingest** -> **Try it out**.
2. Under **file**, click **Choose File** and pick any `.txt` or text-based `.pdf` (not a scanned photo).
3. Under **chunking_strategy**, choose `fixed` or `sentence`.
4. Click **Execute** once.
5. Success: **Code 201** and a response like `{"document_id": "...", "chunk_count": 9, ...}`.

Repeat with the other strategy to try both. (Uploading the same file twice stores it twice, which is harmless.)

### Test 2 - Ask questions (Conversational RAG API)
1. Click **POST /chat** -> **Try it out**.
2. In the **Request body** box, replace everything with a question about your document:
   ```json
   {
     "message": "What is this document about?"
   }
   ```
3. Click **Execute**. Success: **Code 200**, an `answer`, and the `sources` it used.
4. Copy the `session_id` from the response. For a follow-up question, send both fields:
   ```json
   {
     "session_id": "PASTE-THE-ID-HERE",
     "message": "Can you give more detail on that?"
   }
   ```
   The answer shows the chat memory (Redis) working: you did not repeat the topic.

> The box accepts only `session_id` and `message`. Do not paste the response back into it.

### Test 3 - Book an interview
Use the same `session_id`, one message at a time:
1. `"message": "I would like to book an interview"` -> the assistant asks for the missing details.
2. `"message": "My name is Sita Sharma, email sita@gmail.com, November 20 at 3pm"` -> the assistant confirms the booking and returns a `booking_id`.

(You can also give all details in a single message.)

### Test 4 - See stored bookings
Click **GET /bookings** -> **Try it out** -> **Execute**. Your booking is in the list.

### Automated tests (optional)
```
pytest
```
These use a fake AI and fake Redis, so they need no key or internet.

---

## If something goes wrong

| What you see | What it means / fix |
|---|---|
| `llm_api_key Field required` when starting | The `.env` file is missing or in the wrong folder. Redo Step 5; `.env` must sit next to `requirements.txt`. |
| `python` is "not recognized" (Windows) | Use `py` for the first command (`py -m venv .venv`). Inside the activated environment `python` works. |
| **404** error on `/chat` (terminal shows `NotFoundError`) | The AI model name is out of date. Change `LLM_MODEL` in `.env` to a current Gemini model name (see https://ai.google.dev/gemini-api/docs/models) and save. |
| **429** error | Free-tier limit reached. Wait a minute or try a smaller model name. |
| **500** on `/chat` mentioning redis / connection | Check `REDIS_URL`: for Upstash it must start with `rediss://` (two s) and end with `:6379`; for Docker make sure Docker is running. |
| **422** `Field required ... message` | The request box must contain `"message"`. See the note under Test 2. |
| **422** "No readable text" on upload | The PDF is probably a scan. Use a PDF with selectable text. |
| **415** on upload | Only `.pdf` and `.txt` are accepted. |

---

## Project layout

```
app/
  main.py            app startup
  config.py          settings read from .env
  db.py              SQL tables: documents, bookings
  schemas.py         request/response models
  deps.py            builds shared services
  routers/
    ingestion.py     POST /documents/ingest
    chat.py          POST /chat, GET /bookings
  services/
    extraction.py    PDF/TXT -> text
    chunking.py      "fixed" and "sentence" strategies
    llm.py           chat + embeddings (OpenAI-compatible API)
    vector_store.py  Qdrant
    memory.py        Redis chat history + half-finished booking
    ingestion.py     ingestion pipeline
    chat_service.py  custom RAG + booking logic
tests/               unit and end-to-end tests
```

## Design notes
- **Chunking:** `fixed` = 800 characters with 100 overlap; `sentence` = whole sentences packed up to 800 characters.
- **Chat flow:** one LLM call classifies the message (question or booking), rewrites follow-ups into standalone questions, and extracts booking details. Questions go through embed -> Qdrant search -> LLM answer. Bookings are validated (email, date not in the past, time) and saved in SQL once name, email, date and time are all collected.
- **Memory:** the last 10 messages per session are kept in Redis with an expiry (24 hours).
- **Providers:** any OpenAI-compatible provider works through `LLM_BASE_URL` (Gemini by default).
- **Storage:** SQLite and local Qdrant keep setup simple. Set `DATABASE_URL` for PostgreSQL, or `QDRANT_URL` and `QDRANT_API_KEY` for Qdrant Cloud.
- **Secrets:** no keys are committed; use your own `.env`.