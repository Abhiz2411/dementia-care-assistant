# Dementia Care Assistant

A **local-first voice-based cognitive assessment agent** designed for dementia care.  
It uses **XTTS v2** for multilingual voice cloning, **Flask** as the backend, and a **state-machine driven conversation engine** to run cognitive tasks (orientation, memory, attention, planning) with automated scoring.

---

## 📖 Project Description
This is a voice-based assistant that helps assess cognitive function.  
It uses locally-hosted **XTTS v2** text-to-speech to guide users through several phases:  
- Greeting  
- Three-word memory test  
- Intervening cognitive questions  
- Delayed recall  
- Summary with scores  

The system runs in **Auto Mode** by default for a smoother experience.

---

## 🚀 Features
- 🎤 **Voice Cloning (XTTS v2)** – Clone a patient’s voice locally and synthesize speech.  
- 🧠 **Cognitive Test Flow** – Registration, recall, orientation, attention, and planning tasks.  
- 📊 **Automated Scoring** – Domain-wise performance (Excellent, Good, Fair, Needs Attention).  
- 🌐 **Simple Frontend** – HTML/JS interface with mic recording and playback.  
- 🔒 **Local-First** – All TTS runs locally; ASR can be disabled (stub fallback).  

---

## 🛠️ Tech Stack
- **Python 3.10 (recommended)**  
- **Flask** – REST API backend  
- **XTTS v2 (FastAPI server)** – Voice cloning & TTS  
- **Google Gemini ASR** – Speech-to-text (optional, stub fallback)  
- **HTML/JavaScript** – Lightweight frontend  
- **JSON Storage** – Simple persistence for users & voices  

---

## 📂 Project Structure
```
project/
│
├── app.py                # Flask API server
├── xtts_server.py        # Local XTTS v2 FastAPI server
├── services/             # Logic: ASR, XTTS, conversation, scoring
├── data/                 # Questions + user store (JSON)
├── static/               # Frontend (index.html, JS, CSS)
├── uploads/              # Runtime audio uploads
├── voices/               # Stored cloned voices
├── requirements.txt      # Python dependencies
└── docker-compose.yml    # Multi-service deployment (Flask + XTTS)
```

---

## ⚙️ Setup & Run

### 🔹 Requirements
- A computer running Windows, Mac, or Linux with **Python 3.10** installed  
- The XTTS v2 system running on your machine (provided as a FastAPI server)  
- **Optional:** Google Gemini API key if you want speech recognition  

### 🔹 1. Set up your Python environment
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 🔹 2. Create a `.env` file
(or just copy `.env.example`) with these settings:
```
GOOGLE_API_KEY=
XTTS_BASE_URL=http://localhost:8020
GEMINI_ASR_MODEL=gemini-1.5-flash
PORT=5000
```

### 🔹 3. Run the XTTS server
```powershell
python -m uvicorn xtts_server:app --host 0.0.0.0 --port 8020
```

### 🔹 4. Run the Flask app
```powershell
. .venv\Scripts\Activate.ps1
python app.py
```

### 🔹 5. Open in browser
Visit: `http://localhost:5000`

---

## 🐳 Run with Docker Compose
```bash
docker compose up --build
```
- Flask API → `http://localhost:8000`  
- XTTS server → `http://localhost:9000`  

---

## 📊 How to Use
1. Create an account or log in.  
2. Record a voice sample (1–3 minutes) to clone your voice.  
3. Start a new session and begin the test.  
4. Auto Mode (on by default) will:  
   - Speak instructions using your cloned voice  
   - Play a beep when it’s your turn  
   - Record your response  
   - Convert your speech to text (if Gemini is set up)  
   - Move to the next step  
   - Show a nicely formatted summary at the end  

---

## ⚙️ Technical Details
- API has endpoints for session management, voice cloning, text-to-speech, speech recognition, and conversation flow.  
- Questions are stored in **data/questions.json** and support:  
  * Math (addition & subtraction)  
  * Digit repetition  
  * Yes/No questions  
  * Free speech with minimum word requirements  
  * Planning tasks with keyword detection  
- Scoring happens in `services/scoring.py` and results are displayed in the UI.  

---

## 💡 Good to Know
- All text-to-speech runs **locally** – no cloud services required.  
- You can adjust Auto Mode listening time in `static/index.html` (default: 6000ms).  
- For microphone access, use **Chrome/Edge** on localhost or HTTPS.  

---

## 🔮 Future Improvements
- Add **offline ASR** (e.g., Whisper/Faster-Whisper).  
- Expand question set with adaptive difficulty.  
- Store sessions in a database for multi-user scale.  
- Add analytics dashboard for caregivers.  

---

## 📜 License
MIT License – Free to use and modify for research and educational purposes.

---
