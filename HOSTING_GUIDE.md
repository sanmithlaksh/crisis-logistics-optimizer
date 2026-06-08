# Deployment and Development Guide

This guide explains how to host this application for your teammates and how to make future updates as requirements evolve.

---

## Part 1: How to Host the Website

Since the system uses a **Flask backend** and a **Supabase cloud database**, you have three excellent options for sharing it with your teammates.

### Option 1: Local Network (LAN) Sharing (Easiest & Free)
If your teammates are on the same Wi-Fi network or local area network, they can access the website directly from your machine.

1. **Find your local IP address**:
   - Open PowerShell or Command Prompt and run:
     ```powershell
     ipconfig
     ```
   - Look for the **IPv4 Address** under your active network adapter (e.g., `192.168.1.45`).

2. **Run the Flask server on all interfaces**:
   - In `app.py`, change `app.run(debug=True, port=5000)` to:
     ```python
     app.run(host='0.0.0.0', debug=True, port=5000)
     ```
   - Run the app: `python app.py`

3. **Teammates Access**:
   - Your teammates can open their browsers and go to: `http://<your-ip-address>:5000` (e.g., `http://192.168.1.45:5000`).
   - *Note: Ensure your Windows Firewall allows inbound connections on port 5000.*

---

### Option 2: Share via Ngrok Tunnel (Fastest for Remote Teammates)
If your teammates are remote (not on your Wi-Fi) and you want to give them immediate, secure access without deploying to the cloud:

1. Download and install [Ngrok](https://ngrok.com/).
2. Run your Flask app locally:
   ```bash
   python app.py
   ```
3. Open a new terminal and run:
   ```bash
   ngrok http 5000
   ```
4. Ngrok will provide a public forwarding URL (e.g., `https://xxxx.ngrok-free.app`). Share this URL with your teammates.

---

### Option 3: Deploy to Cloud Hosting (Best for Permanent Access)
You can host the website permanently on platforms like **Render**, **Railway**, or **Fly.io** (which all have free tiers).

#### Example: Deploying to Render
1. **Prepare the codebase**:
   - Create a `requirements.txt` file listing the dependencies:
     ```text
     Flask>=2.0.0
     supabase>=2.0.0
     python-dotenv>=1.0.0
     ```
   - Create a `Procfile` (tells Render how to run the app using a production server like Gunicorn):
     ```text
     web: gunicorn app:app
     ```
2. **Push code to GitHub**:
   - Initialize a git repo, commit your code, and push it to a private or public GitHub repository.
3. **Link to Render**:
   - Create a free account on [Render](https://render.com/).
   - Click **New** -> **Web Service** and connect your GitHub repository.
4. **Configure Environment Variables**:
   - In the Render dashboard, go to **Environment** and add the variables from your local `.env` file:
     - `SUPABASE_URL`
     - `SUPABASE_KEY`
5. **Deploy**:
   - Render will build the project and assign a public URL (e.g., `https://crisis-optimizer.onrender.com`).

---

## Part 2: How to Update the Website

Here is how the project structure is organized so you can make updates:

```text
DAA/
├── algorithms/                 # <--- CORE DAA ALGORITHMS
│   ├── priority_queue.py       # Max-Heap logic
│   ├── resource_allocation.py  # Greedy resource distribution logic
│   ├── dijkstra.py            # Risk-weighted routing logic
│   ├── knapsack.py            # 0/1 Knapsack DP cargo optimizer
│   └── branch_bound.py        # Branch & Bound fleet assignment logic
├── static/                     # <--- FRONTEND STATIC ASSETS
│   ├── css/
│   │   └── style.css           # UI layout, glassmorphism, glowing paths
│   └── js/
│       ├── charts.js           # Chart.js analytics logic
│       ├── map.js              # Leaflet.js interactive map logic
│       └── dashboard.js        # Tab navigation, forms, and API requests
├── templates/
│   └── index.html              # HTML markup shell
├── app.py                      # Flask web server & API routes
├── database.py                 # Supabase client wrapper & local fallback
└── simulation.py               # Handles the 4 scenario runs
```

### 1. Changing the Algorithms (Logic Updates)
- To tweak the **Dijkstra risk weightings**: Open [algorithms/dijkstra.py](file:///h:/DAA/algorithms/dijkstra.py) and modify the edge cost calculation.
- To change **Heap Priority metrics**: Open [algorithms/priority_queue.py](file:///h:/DAA/algorithms/priority_queue.py) and edit the score weighting calculation in `RequestItem.__init__`.
- To modify **Knapsack values**: Open [algorithms/knapsack.py](file:///h:/DAA/algorithms/knapsack.py).

### 2. Changing the UI (Design Updates)
- To change **colors, fonts, or styling**: Edit [static/css/style.css](file:///h:/DAA/static/css/style.css).
- To add **new tabs or input fields**: Modify [templates/index.html](file:///h:/DAA/templates/index.html) and add corresponding DOM event listeners in [static/js/dashboard.js](file:///h:/DAA/static/js/dashboard.js).

### 3. Adding New Scenarios
- If you need to add a new disaster scenario (e.g., "Volcano Eruption"), open [simulation.py](file:///h:/DAA/simulation.py).
- Add the scenario name and define which road connections become blocked, flooded, or damaged in that scenario.
- Add the scenario as an `<option>` in [templates/index.html](file:///h:/DAA/templates/index.html).
