from flask import Flask, request, jsonify, render_template_string
from kubernetes import client, config
import requests
import os

app = Flask(__name__)

# Try to load incluster config first, then kube config
try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        print("Could not load kubernetes configuration")

v1 = client.CoreV1Api()

OLLAMA_URL = "http://ollama.ai-ops.svc.cluster.local:11434/api/generate"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Log Analyzer</title>
    <!-- Import Marked.js for Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        
        * { box-sizing: border-box; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-page);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }

        /* Navbar */
        nav {
            width: 100%;
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            padding: 1rem 0;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            margin-bottom: 2rem;
        }
        .nav-content {
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            padding: 0 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .nav-icon { font-size: 1.5rem; }
        .nav-title {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            color: var(--text-main);
        }
        .author-badge {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            font-size: 0.875rem;
        }
        .author-name {
            font-weight: 600;
            color: var(--text-main);
        }
        .author-role {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Main Workspace */
        main {
            width: 100%;
            max-width: 800px;
            padding: 0 1rem 3rem 1rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        /* Card Component */
        .card {
            background: var(--bg-card);
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            overflow: hidden;
            border: 1px solid var(--border);
        }

        /* Hero Banner */
        .banner-container {
            width: 100%;
            height: 220px;
            background-color: #f1f5f9;
            position: relative;
        }
        .banner-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .banner-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
            padding: 1.5rem;
            color: white;
        }
        .banner-title {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        /* Form Area */
        .card-body { padding: 2rem; }
        
        .form-grid { display: grid; gap: 1.5rem; }
        .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
        
        label {
            font-size: 0.875rem;
            font-weight: 600;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        select {
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            background-color: #fff;
            transition: border-color 0.2s;
            color: var(--text-main);
            appearance: none;
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
            background-position: right 0.75rem center;
            background-repeat: no-repeat;
            background-size: 1.5em 1.5em;
        }
        select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        select:disabled {
            background-color: #f8fafc;
            color: #94a3b8;
            cursor: not-allowed;
        }

        .btn-primary {
            background-color: var(--primary);
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            width: 100%;
            font-size: 1rem;
            transition: all 0.2s;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .btn-primary:hover:not(:disabled) {
            background-color: var(--primary-hover);
            transform: translateY(-1px);
        }
        .btn-primary:disabled {
            background-color: #cbd5e1;
            cursor: not-allowed;
            transform: none;
        }

        /* Spinner Animation */
        .spinner {
            display: none;
            width: 1.25rem;
            height: 1.25rem;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s ease-in-out infinite;
            margin-right: 0.75rem;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Results Area */
        #result-area {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 2.5rem;
            display: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        
        #result-area h1, #result-area h2 { color: var(--text-main); margin-top: 1.5rem; }
        #result-area h1 { margin-top: 0; padding-bottom: 0.5rem; border-bottom: 2px solid #f1f5f9; }
        #result-area pre { 
            background: #1e293b; 
            color: #f8fafc; 
            padding: 1rem; 
            border-radius: 0.5rem; 
            overflow-x: auto; 
        }

        /* Footer */
        footer {
            margin-top: auto;
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        .footer-content {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
    </style>
</head>
<body>
    <nav>
        <div class="nav-content">
            <div class="brand">
                <span class="nav-icon">🛡️</span>
                <span class="nav-title">AI Log Analyzer</span>
            </div>
            <div class="author-badge">
                <span class="author-name">Ajit Kumar</span>
                <span class="author-role">Senior Technology Engineer</span>
            </div>
        </div>
    </nav>

    <main>
        <div class="card">
            <div class="banner-container">
                <img src="/static/background.png" alt="Dashboard Banner" class="banner-img">
                <div class="banner-overlay">
                    <h2 class="banner-title">Kubernetes Diagnostics</h2>
                </div>
            </div>
            
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="namespace">Namespace</label>
                        <select id="namespace">
                            <option value="">Select Namespace</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="pod">Pod</label>
                        <select id="pod" disabled>
                            <option value="">Select Pod</option>
                        </select>
                    </div>

                    <button id="analyze-btn" class="btn-primary" disabled>
                        <span class="spinner" id="btn-spinner"></span>
                        <span id="btn-text">Analyze Issue</span>
                    </button>
                </div>
            </div>
        </div>

        <div id="result-area"></div>
    </main>

    <footer>
        <div class="footer-content">
            <span>&copy; 2026 Project</span>
            <span>Designed & Developed by <strong>Ajit Kumar</strong></span>
        </div>
    </footer>

    <script>
        const nsSelect = document.getElementById('namespace');
        const podSelect = document.getElementById('pod');
        const analyzeBtn = document.getElementById('analyze-btn');
        const btnText = document.getElementById('btn-text');
        const btnSpinner = document.getElementById('btn-spinner');
        const resultArea = document.getElementById('result-area');

        // Fetch Namespaces
        fetch('/api/namespaces')
            .then(res => res.json())
            .then(data => {
                if (data.error) return console.error(data.error);
                data.forEach(ns => {
                    const opt = document.createElement('option');
                    opt.value = ns;
                    opt.textContent = ns;
                    nsSelect.appendChild(opt);
                });
            })
            .catch(err => console.error(err));

        nsSelect.addEventListener('change', () => {
            const ns = nsSelect.value;
            podSelect.innerHTML = '<option value="">Select Pod</option>';
            podSelect.disabled = !ns;
            analyzeBtn.disabled = true;
            
            if (ns) {
                fetch(`/api/pods/${ns}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.error) return console.error(data.error);
                        data.forEach(pod => {
                            const opt = document.createElement('option');
                            opt.value = pod;
                            opt.textContent = pod;
                            podSelect.appendChild(opt);
                        });
                    })
                    .catch(e => console.error(e));
            }
        });

        podSelect.addEventListener('change', () => {
            analyzeBtn.disabled = !podSelect.value;
        });

        analyzeBtn.addEventListener('click', () => {
            const ns = nsSelect.value;
            const pod = podSelect.value;
            
            // Set Loading State
            btnText.textContent = 'Running Diagnostics...';
            btnSpinner.style.display = 'block';
            analyzeBtn.disabled = true;
            resultArea.style.opacity = '0.5';

            fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ namespace: ns, pod: pod })
            })
            .then(res => res.json())
            .then(data => {
                resultArea.style.display = 'block';
                resultArea.style.opacity = '1';
                
                if (data.result) {
                    resultArea.innerHTML = marked.parse(data.result);
                    resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
                } else {
                    resultArea.innerHTML = `<h3 style="color:#ef4444;">Analysis Failed</h3><p>${data.error || "Unknown error"}</p>`;
                }
            })
            .catch(err => {
                resultArea.style.display = 'block';
                resultArea.innerHTML = `<h3 style="color:#ef4444;">Network Error</h3><p>${err.message}</p>`;
            })
            .finally(() => {
                // Reset Loading State
                btnText.textContent = 'Analyze Issue';
                btnSpinner.style.display = 'none';
                analyzeBtn.disabled = false;
            });
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template_string(HTML)

@app.route("/api/namespaces", methods=["GET"])
def get_namespaces():
    try:
        namespaces = v1.list_namespace()
        return jsonify([ns.metadata.name for ns in namespaces.items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pods/<namespace>", methods=["GET"])
def get_pods(namespace):
    try:
        pods = v1.list_namespaced_pod(namespace)
        return jsonify([pod.metadata.name for pod in pods.items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    ns = data.get("namespace")
    pod = data.get("pod")

    if not ns or not pod:
        return jsonify({"error": "Missing namespace or pod"}), 400

    try:
        # 1. Fetch Pod Data
        pod_obj = v1.read_namespaced_pod(pod, ns)
        
        # 2. Fetch Events (Critical for scheduling/secrets/configmap/init issues)
        events = v1.list_namespaced_event(ns, field_selector=f"involvedObject.name={pod}")
        event_log = "\n".join([f"- [{e.type}] {e.reason}: {e.message}" for e in events.items])

        # 3. Fetch Logs (Last 50 lines)
        try:
            logs = v1.read_namespaced_pod_log(pod, ns, tail_lines=50)
        except Exception:
            logs = "Logs unavailable (Pod might be failing to start)."

        # 4. Comprehensive Status Analysis
        diagnostics = []

        # Check Node Scheduling (Pending state context)
        for cand in pod_obj.status.conditions or []:
            if cand.type == "PodScheduled" and cand.status == "False":
                diagnostics.append(f"SCHEDULING ERROR: {cand.message}")
        
        # Check Init Containers
        if pod_obj.status.init_container_statuses:
            for c in pod_obj.status.init_container_statuses:
                if not c.ready:
                    state_reason = c.state.waiting.reason if c.state.waiting else (c.state.terminated.reason if c.state.terminated else "Unknown")
                    diagnostics.append(f"INIT CONTAINER '{c.name}' FAILED. State: {state_reason}")

        # Check Main Containers
        if pod_obj.status.container_statuses:
            for c in pod_obj.status.container_statuses:
                if not c.ready:
                    if c.state.waiting:
                         diagnostics.append(f"CONTAINER '{c.name}' WAITING. Reason: {c.state.waiting.reason}")
                    elif c.state.terminated:
                         diagnostics.append(f"CONTAINER '{c.name}' TERMINATED. Exit Code: {c.state.terminated.exit_code}. Reason: {c.state.terminated.reason}")
        
        # Determine Context
        if not diagnostics and pod_obj.status.phase == "Running":
            context = "The Pod is in a RUNNING state and appears healthy."
        elif not diagnostics and pod_obj.status.phase == "Pending":
            context = "The Pod is PENDING but no specific container failure found. Likely waiting for resources or scheduling."
        else:
            context = "CRITICAL ISSUES FOUND:\n" + "\n".join(diagnostics)

        prompt = f"""
You are an expert Kubernetes SRE. Analyze this pod failure.

DETAILS:
Namespace: {ns}
Pod: {pod}
Status Phase: {pod_obj.status.phase}

DIAGNOSTIC CONTEXT:
{context}

EVENTS:
{event_log}

LOGS:
{logs}

STRICT INSTRUCTIONS:
You must provide the analysis in the EXACT following Markdown format. Do not add introductions or conclusions.

# 🚨 Root Cause Analysis
[Explain precisely what caused the failure in 1-2 sentences]

# 🔍 Technical Details
[Bullet points explaining the technical evidence from logs/events]

# 🛠️ Actionable Fix
[Specific kubectl commands or YAML changes to fix this]

# 📋 Prevention
[One tip to prevent this in future]

"""

        r = requests.post(OLLAMA_URL, json={
            # "model": "llama3",
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }, timeout=300)
        
        if r.status_code == 200:
            result = r.json().get("response", "No response from AI")
        else:
            result = f"Error from AI service: {r.status_code} {r.text}"

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
