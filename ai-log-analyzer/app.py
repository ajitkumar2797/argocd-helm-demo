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

# OLLAMA_URL = "http://ollama.ai-ops.svc.cluster.local:11434/api/generate"
OLLAMA_URL = "http://host.minikube.internal:11434/api/generate"

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
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 1.5rem;
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
            max-width: 1000px;
            padding: 0 1.5rem 3rem 1.5rem;
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
                        <label for="resource-type">Resource Type</label>
                        <select id="resource-type" disabled>
                            <option value="Pod">Pod</option>
                            <option value="Deployment">Deployment</option>
                            <option value="StatefulSet">StatefulSet</option>
                        </select>
                    </div>

                    <div class="form-group" id="controller-group" style="display:none;">
                        <label for="controller-name">Workload Name</label>
                         <select id="controller-name">
                            <option value="">Select Workload</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="pod">Target Pod</label>
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

        <!-- Interactive Chat Section -->
        <div id="chat-section" style="display:none; margin-top: 2rem;">
            <div class="card" style="padding: 1.5rem;">
                <h3 style="margin-top:0; color:var(--text-main); display:flex; align-items:center; gap:0.5rem;">
                    💬 AI SRE Assistant
                    <span style="font-size:0.8rem; font-weight:normal; color:var(--text-muted);">(Ask follow-up questions)</span>
                </h3>
                <div id="chat-history" style="max-height: 300px; overflow-y: auto; margin-bottom: 1rem; border: 1px solid var(--border); border-radius: 0.5rem; padding: 1rem; background: #f8fafc;">
                    <!-- Chat messages go here -->
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <input type="text" id="chat-input" placeholder="e.g. 'Write a Helm patch for this' or 'Explain to a junior dev'" style="flex:1; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem;">
                    <button id="send-chat-btn" class="btn-primary" style="width: auto; margin-top:0;">Send</button>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <div class="footer-content">
            <span>&copy; 2026 Project</span>
            <span>Designed & Developed by <strong>Ajit Kumar</strong></span>
        </div>
    </footer>

    <script>
        const nsSelect = document.getElementById('namespace');
        const typeSelect = document.getElementById('resource-type');
        const ctrlGroup = document.getElementById('controller-group');
        const ctrlSelect = document.getElementById('controller-name');
        const podSelect = document.getElementById('pod');
        
        const analyzeBtn = document.getElementById('analyze-btn');
        const btnText = document.getElementById('btn-text');
        const btnSpinner = document.getElementById('btn-spinner');
        const resultArea = document.getElementById('result-area');
        
        // Chat Elements
        const chatSection = document.getElementById('chat-section');
        const chatHistory = document.getElementById('chat-history');
        const chatInput = document.getElementById('chat-input');
        const sendChatBtn = document.getElementById('send-chat-btn');
        
        let currentContext = ""; 

        // 1. Fetch Namespaces
        fetch('/api/namespaces')
            .then(res => res.json())
            .then(data => {
                if(data.error) return console.error(data.error);
                data.forEach(ns => {
                    const opt = document.createElement('option');
                    opt.value = ns;
                    opt.textContent = ns;
                    nsSelect.appendChild(opt);
                });
            })
            .catch(console.error);

        // 2. Handle Namespace Change
        nsSelect.addEventListener('change', () => {
             const ns = nsSelect.value;
             
             // Reset downstream
             typeSelect.value = "Pod"; 
             typeSelect.disabled = !ns;
             ctrlGroup.style.display = 'none';
             ctrlSelect.innerHTML = '<option value="">Select Workload</option>';
             podSelect.innerHTML = '<option value="">Select Pod</option>';
             podSelect.disabled = true;
             analyzeBtn.disabled = true;
             chatSection.style.display = 'none';

             if (ns) {
                 // Default to listing all pods (Pod Mode)
                 fetchPods(ns);
             }
        });

        // 3. Handle Type Change
        typeSelect.addEventListener('change', () => {
            const ns = nsSelect.value;
            const type = typeSelect.value;
            
            ctrlSelect.innerHTML = '<option value="">Select Workload</option>';
            podSelect.innerHTML = '<option value="">Select Pod</option>';
            podSelect.disabled = true;
            analyzeBtn.disabled = true;

            if (type === 'Pod') {
                ctrlGroup.style.display = 'none';
                fetchPods(ns);
            } else {
                ctrlGroup.style.display = 'flex';
                // Fetch Deployments or StatefulSets
                const endpoint = type === 'Deployment' ? 'deployments' : 'statefulsets';
                fetch(`/api/${endpoint}/${ns}`)
                    .then(res => res.json())
                    .then(data => {
                         data.forEach(name => {
                             const opt = document.createElement('option');
                             opt.value = name;
                             opt.textContent = name;
                             ctrlSelect.appendChild(opt);
                         });
                    });
            }
        });

        // 4. Handle Workload Selection (Deployment/STS)
        ctrlSelect.addEventListener('change', () => {
             const ns = nsSelect.value;
             const type = typeSelect.value;
             const name = ctrlSelect.value;
             
             podSelect.innerHTML = '<option value="">Select Pod</option>';
             
             if(name) {
                 fetch('/api/pods_controller', {
                     method: 'POST',
                     headers: {'Content-Type': 'application/json'},
                     body: JSON.stringify({ namespace: ns, kind: type, name: name })
                 })
                 .then(res => res.json())
                 .then(data => {
                     if(data.length === 0) {
                         const opt = document.createElement('option');
                         opt.textContent = "No pods found";
                         podSelect.appendChild(opt);
                     } else {
                         data.forEach(pod => {
                             const opt = document.createElement('option');
                             opt.value = pod;
                             opt.textContent = pod;
                             podSelect.appendChild(opt);
                         });
                         podSelect.disabled = false;
                     }
                 });
             }
        });

        // Helper: Fetch all pods (Default behavior)
        function fetchPods(ns) {
            fetch(`/api/pods/${ns}`)
                .then(res => res.json())
                .then(data => {
                    data.forEach(pod => {
                        const opt = document.createElement('option');
                        opt.value = pod;
                        opt.textContent = pod;
                        podSelect.appendChild(opt);
                    });
                    podSelect.disabled = false;
                });
        }

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
            chatSection.style.display = 'none';
            chatHistory.innerHTML = ''; // Clear previous chat

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
                    currentContext = data.full_context; // Save context for chat
                    resultArea.innerHTML = marked.parse(data.result);
                    
                    // Add Copy Buttons
                    document.querySelectorAll('pre code').forEach((block) => {
                         const button = document.createElement('button');
                         button.innerText = 'Copy';
                         button.className = 'copy-btn';
                         button.style.cssText = 'float:right; padding:2px 8px; font-size:12px; cursor:pointer; background:#2563eb; color:white; border:none; border-radius:4px; margin-left:10px;';
                         button.addEventListener('click', () => {
                             navigator.clipboard.writeText(block.innerText).then(() => {
                                 button.innerText = 'Copied!';
                                 setTimeout(() => button.innerText = 'Copy', 2000);
                             });
                         });
                         const pre = block.parentNode;
                         pre.insertBefore(button, pre.firstChild);
                    });

                    // Add Download Button
                    if (!document.getElementById('download-btn')) {
                         const btnContainer = document.createElement('div');
                         btnContainer.style.marginTop = '1rem';
                         btnContainer.style.display = 'flex';
                         btnContainer.style.gap = '1rem';

                         // Download Button
                         const dlBtn = document.createElement('button');
                         dlBtn.id = 'download-btn';
                         dlBtn.innerText = '📄 Download Report';
                         dlBtn.className = 'btn-primary';
                         dlBtn.style.backgroundColor = '#10b981'; 
                         dlBtn.style.width = 'auto'; 
                         dlBtn.style.margin = '0';
                         
                         dlBtn.onclick = () => {
                             const blob = new Blob([data.result], { type: 'text/markdown' });
                             const url = window.URL.createObjectURL(blob);
                             const a = document.createElement('a');
                             a.href = url;
                             a.download = `analysis-${pod}-${new Date().toISOString().slice(0,10)}.md`;
                             document.body.appendChild(a);
                             a.click();
                             document.body.removeChild(a);
                         };
                         
                         // Jira Button
                         const jiraBtn = document.createElement('button');
                         jiraBtn.id = 'jira-btn';
                         jiraBtn.innerText = '🎫 Create Jira Ticket';
                         jiraBtn.className = 'btn-primary';
                         jiraBtn.style.backgroundColor = '#0052CC'; // Jira Blue
                         jiraBtn.style.width = 'auto'; 
                         jiraBtn.style.margin = '0';

                         jiraBtn.onclick = () => {
                             jiraBtn.disabled = true;
                             jiraBtn.innerText = 'Creating...';
                             
                             fetch('/api/create_jira', {
                                 method: 'POST',
                                 headers: {'Content-Type': 'application/json'},
                                 body: JSON.stringify({
                                     summary: `[AI Analysis] Incident in pod ${pod}`,
                                     description: data.result,
                                     pod: pod
                                 })
                             })
                             .then(res => res.json())
                             .then(j => {
                                 if(j.ticket_url) {
                                     jiraBtn.innerText = 'Ticket Created ↗';
                                     jiraBtn.onclick = () => window.open(j.ticket_url, '_blank');
                                     alert(`Ticket ${j.key} created successfully!`);
                                 } else {
                                     jiraBtn.innerText = 'Failed';
                                     alert('Error creating ticket: ' + j.error);
                                 }
                             })
                             .catch(e => {
                                 console.error(e);
                                 jiraBtn.innerText = 'Error';
                             });
                         };

                         btnContainer.appendChild(dlBtn);
                         btnContainer.appendChild(jiraBtn);
                         resultArea.appendChild(btnContainer);
                    }

                    // Show Chat Section
                    chatSection.style.display = 'block';
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
                btnText.textContent = 'Analyze Issue';
                btnSpinner.style.display = 'none';
                analyzeBtn.disabled = false;
            });
        });

        // Chat Logic
        sendChatBtn.addEventListener('click', () => {
             const question = chatInput.value.trim();
             if (!question) return;

             // Add User Message
             const userMsg = document.createElement('div');
             userMsg.innerHTML = `<strong>You:</strong> ${question}`;
             userMsg.style.marginBottom = '0.5rem';
             userMsg.style.color = '#2563eb';
             chatHistory.appendChild(userMsg);
             
             chatInput.value = '';
             sendChatBtn.disabled = true;
             sendChatBtn.textContent = '...';

             fetch('/chat', {
                 method: 'POST',
                 headers: {'Content-Type': 'application/json'},
                 body: JSON.stringify({ context: currentContext, question: question })
             })
             .then(res => res.json())
             .then(data => {
                 const aiMsg = document.createElement('div');
                 aiMsg.innerHTML = `<strong>AI:</strong> ${marked.parse(data.response)}`;
                 aiMsg.style.marginBottom = '1rem';
                 aiMsg.style.padding = '0.5rem';
                 aiMsg.style.background = 'white';
                 aiMsg.style.borderRadius = '0.5rem';
                 chatHistory.appendChild(aiMsg);
                 chatHistory.scrollTop = chatHistory.scrollHeight;
             })
             .catch(console.error)
             .finally(() => {
                 sendChatBtn.disabled = false;
                 sendChatBtn.textContent = 'Send';ls
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

@app.route("/api/deployments/<namespace>", methods=["GET"])
def get_deployments(namespace):
    try:
        apps_v1 = client.AppsV1Api()
        deps = apps_v1.list_namespaced_deployment(namespace)
        return jsonify([d.metadata.name for d in deps.items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/statefulsets/<namespace>", methods=["GET"])
def get_statefulsets(namespace):
    try:
        apps_v1 = client.AppsV1Api()
        sts = apps_v1.list_namespaced_stateful_set(namespace)
        return jsonify([s.metadata.name for s in sts.items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pods_controller", methods=["POST"])
def get_pods_controller():
    # Fetch pods belonging to a controller via MatchLabels
    data = request.json
    ns = data.get('namespace')
    kind = data.get('kind') # Deployment, StatefulSet, Pods
    name = data.get('name')

    if kind == "Pod":
        # logic handled by normal pod list, but if this is called with "Pod", we just return empty or handle differently
        return jsonify([])

    try:
        apps_v1 = client.AppsV1Api()
        labels = {}
        
        if kind == 'Deployment':
            c = apps_v1.read_namespaced_deployment(name, ns)
            labels = c.spec.selector.match_labels
        elif kind == 'StatefulSet':
            c = apps_v1.read_namespaced_stateful_set(name, ns)
            labels = c.spec.selector.match_labels
        
        if not labels:
             return jsonify([])

        selector = ",".join([f"{k}={v}" for k, v in labels.items()])
        pods = v1.list_namespaced_pod(ns, label_selector=selector)
        
        return jsonify([p.metadata.name for p in pods.items])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/create_jira", methods=["POST"])
def create_jira():
    data = request.json
    summary = data.get('summary')
    description = data.get('description')
    
    # Load Credentials from Environment
    JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
    EMAIL = os.getenv("JIRA_EMAIL")
    API_TOKEN = os.getenv("JIRA_API_TOKEN")
    PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

    if not all([JIRA_DOMAIN, EMAIL, API_TOKEN, PROJECT_KEY]):
        return jsonify({"error": "Jira credentials not configured in Pod Environment"}), 500

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"
    auth = (EMAIL, API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    # Jira Cloud Document Format (Required for 'description')
    # Use a simple ADF structure
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description[:3000] # Truncate to avoid payload limits
                    }
                ]
            }
        ]
    }

    payload = {
        "fields": {
           "project": {"key": PROJECT_KEY},
           "summary": summary,
           "description": adf_description, 
           "issuetype": {"name": "Bug"}
       }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        if response.status_code == 201:
            ticket = response.json()
            return jsonify({
                "key": ticket['key'],
                "ticket_url": f"https://{JIRA_DOMAIN}/browse/{ticket['key']}",
                "message": "Ticket created successfully"
            })
        else:
            return jsonify({"error": f"Jira API Error: {response.text}"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    context = data.get("context", "")
    question = data.get("question", "")
    
    prompt = f"""
You are a Kubernetes Expert Assistant. 
Here is the context of the pod issue we analyzed:
{context}

USER QUESTION: {question}

Provide a helpful, technical answer. If code is needed, use code blocks.
"""
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        
        return jsonify({"response": r.json().get("response", "Error")})
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
        pod_obj = v1.read_namespaced_pod(pod, ns)
        
        # Events
        events = v1.list_namespaced_event(ns, field_selector=f"involvedObject.name={pod}")
        event_log = "\n".join([f"- [{e.type}] {e.reason}: {e.message}" for e in events.items])

        # Logs
        try:
            logs = v1.read_namespaced_pod_log(pod, ns, tail_lines=50)
        except Exception:
            logs = "Logs unavailable."

        # Diagnostics & Metrics
        diagnostics = []
        metrics_info = ""
        
        # METRICS (New Feature)
        try:
            # Attempt to fetch from Metrics Server
            custom_api = client.CustomObjectsApi()
            pod_metrics = custom_api.get_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1", namespace=ns, plural="pods", name=pod
            )
            containers_usage = pod_metrics.get('containers', [])
            metrics_info = "\nLIVE METRICS:\n"
            for c in containers_usage:
                metrics_info += f"- Container '{c['name']}': CPU={c['usage']['cpu']}, Ram={c['usage']['memory']}\n"
        except Exception:
            metrics_info = "\nLIVE METRICS: Metrics Server not available or pod not running.\n"

        resource_issues = []
        for c in pod_obj.spec.containers:
            limits = c.resources.limits or {}
            requests_res = c.resources.requests or {}
            if not limits:
                 resource_issues.append(f"Container '{c.name}' has NO resource limits defined.")
            if not requests_res:
                 resource_issues.append(f"Container '{c.name}' has NO resource requests defined.")
        
        if resource_issues:
            context_resources = "\nCONFIGURATION WARNINGS:\n" + "\n".join(resource_issues)
        else:
            context_resources = "\nResources: Configured correctly."

        # Status Checks
        for cand in pod_obj.status.conditions or []:
            if cand.type == "PodScheduled" and cand.status == "False":
                diagnostics.append(f"SCHEDULING ERROR: {cand.message}")
        
        if pod_obj.status.init_container_statuses:
            for c in pod_obj.status.init_container_statuses:
                if not c.ready:
                    state_reason = c.state.waiting.reason if c.state.waiting else (c.state.terminated.reason if c.state.terminated else "Unknown")
                    diagnostics.append(f"INIT CONTAINER '{c.name}' FAILED. State: {state_reason}")

        if pod_obj.status.container_statuses:
            for c in pod_obj.status.container_statuses:
                if not c.ready:
                    if c.state.waiting:
                         diagnostics.append(f"CONTAINER '{c.name}' WAITING. Reason: {c.state.waiting.reason}")
                    elif c.state.terminated:
                         diagnostics.append(f"CONTAINER '{c.name}' TERMINATED. Exit Code: {c.state.terminated.exit_code}. Reason: {c.state.terminated.reason}")
        
        # Determine Context
        is_healthy = False
        if pod_obj.status.phase == "Running":
             # Check if all containers are actually ready
             all_ready = True
             if pod_obj.status.container_statuses:
                 for c in pod_obj.status.container_statuses:
                     if not c.ready:
                         all_ready = False
                         break
             if all_ready and not diagnostics:
                 is_healthy = True

        log_is_critical = False
        if isinstance(logs, str) and any(x in logs.lower() for x in ["error", "exception", "fatal", "invalid", "panic"]):
            log_is_critical = True

        # If logs have critical errors, suppress the generic resource warnings to keep AI focused
        if log_is_critical:
            context_resources = "" 
        
        if is_healthy:
            context = "The Pod is in a RUNNING state and appears healthy." + context_resources + metrics_info
        elif pod_obj.status.phase == "Pending":
            context = "The Pod is PENDING. " + context_resources
        else:
            context = "CRITICAL ISSUES FOUND:\n" + "\n".join(diagnostics) + context_resources + metrics_info
        
        full_context_str = f"Context: {context}\nEvents: {event_log}\nLogs: {logs}"

        # Define Prompts based on health
        if is_healthy:
            # HEALTHY POD TEMPLATE
            prompt = f"""
You are an expert Kubernetes SRE. Perform a health check.

DETAILS:
Namespace: {ns}
Pod: {pod}
Status Phase: {pod_obj.status.phase}

CONTEXT:
{context}

EVENTS:
{event_log}

LOGS:
{logs}

STRICT INSTRUCTIONS:
You must provide the report in the EXACT following Markdown format. Do not add introductions.

# ✅ Health Status
[Confirm the healthy status in 1 sentence]

# 📊 Live Diagnostics & Metrics
[Bullet points on image status, restarts, and live CPU/Memory if available]

# 🔎 Log Patterns 
[Analyze any INFO/WARN logs]

# 💡 Optimization Tip
[One best practice tip]
"""
        else:
            # FAILURE/ISSUE TEMPLATE
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
[Look for EXPLICIT ERROR MESSAGES in the LOGS first. 
- If "Connection refused" or "Timeout": Suspect Network/DB/Service not ready.
- If "Access denied" or "Auth failed": Suspect Secrets/Passwords.
- If "Invalid config": Suspect ConfigMap/Env Vars.
State the exact error found as the primary root cause.]

# 🔍 Technical Details
[Bullet points explaining technical evidence. Quote specific log lines. Check if it's an Application Error vs Infrastructure Error.]

# 🛠️ Actionable Fix
[Specific kubectl commands or YAML changes to fix this. e.g. 'Check NetworkPolicy', 'Verify Secret credentials', 'Edit ConfigMap']

# 📋 Prevention
[One tip to prevent this specific issue]
"""

        r = requests.post(OLLAMA_URL, json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }, timeout=300)
        
        result = r.json().get("response", "No response from AI")
        
        return jsonify({"result": result, "full_context": full_context_str})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


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

        # Check Resources (Enterprise Best Practice Check)
        resource_issues = []
        for c in pod_obj.spec.containers:
            limits = c.resources.limits or {}
            requests_res = c.resources.requests or {}
            if not limits:
                 resource_issues.append(f"Container '{c.name}' has NO resource limits defined (Security Risk).")
            if not requests_res:
                 resource_issues.append(f"Container '{c.name}' has NO resource requests defined (Scheduler Blindness).")
        
        if resource_issues:
            context_resources = "\nCONFIGURATION WARNINGS:\n" + "\n".join(resource_issues)
        else:
            context_resources = "\nResources: Configured correctly (Limits/Requests present)."

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
            context = "The Pod is in a RUNNING state and appears healthy." + context_resources
        elif not diagnostics and pod_obj.status.phase == "Pending":
            context = "The Pod is PENDING. " + context_resources
        else:
            context = "CRITICAL ISSUES FOUND:\n" + "\n".join(diagnostics) + context_resources

        # Define Prompts based on health
        if not diagnostics and pod_obj.status.phase == "Running":
            # HEALTHY POD TEMPLATE
            prompt = f"""
You are an expert Kubernetes SRE. Perform a health check on this running pod.

DETAILS:
Namespace: {ns}
Pod: {pod}
Status Phase: {pod_obj.status.phase}

CONTEXT:
{context}

EVENTS:
{event_log}

LOGS:
{logs}

STRICT INSTRUCTIONS:
You must provide the report in the EXACT following Markdown format. Do not add introductions.

# ✅ Health Status
[Confirm the healthy status in 1 sentence, e.g. "The pod is healthy and operating normally."]

# 📊 Live Diagnostics
[Bullet points confirming:
- Image pull status
- Container readiness
- Any recent restarts (if any)]

# 🔎 Log Patterns 
[Analyze any INFO/WARN logs. If logs are clean, state "No anomalies detected in application logs."]

# 💡 Optimization Tip
[One general best practice tip for this type of workload (e.g. resource limits, liveness probes)]
"""
        else:
            # FAILURE/ISSUE TEMPLATE
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
[Bullet points explaining the technical evidence from logs/events, e.g. "Exit Code 137 indicates OOMKilled", "401 Unauthorized in logs"]

# 🛠️ Actionable Fix
[Specific kubectl commands or YAML changes to fix this]

# 📋 Prevention
[One tip to prevent this in future]
"""

        r = requests.post(OLLAMA_URL, json={
            "model": "llama3",
            # "model": "phi3",
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
