"""
FastAPI chat server: on-demand marketing requests via HTTP.
POST /chat        → free-form chat with the agent
GET  /queue       → view pending approvals
POST /approve/:id → approve and post
POST /reject/:id  → reject
GET  /reports     → list auto reports (monitor, analytics)
"""
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from memory import get_pending, update_status, get_conn
from agent import chat as agent_chat
from tools.reddit import post_to_reddit
from tools.email_tool import send_campaign
from tools.linkedin import queue_linkedin_draft

app = FastAPI(title="GhostDesk Marketing Agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    reply = agent_chat(req.message)
    return ChatResponse(reply=reply)


@app.get("/queue")
def get_queue():
    return get_pending()


@app.post("/approve/{item_id}")
def approve(item_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Item not found")

    task_type = row["task_type"]
    success = False

    if task_type == "reddit_post":
        success = post_to_reddit(item_id)
    elif task_type == "email":
        success = send_campaign(item_id)
    elif task_type in ("linkedin_draft", "monitor_report", "analytics"):
        update_status(item_id, "approved")
        success = True
    else:
        update_status(item_id, "approved")
        success = True

    return {"success": success, "item_id": item_id, "task_type": task_type}


@app.post("/reject/{item_id}")
def reject(item_id: int):
    update_status(item_id, "rejected")
    return {"rejected": item_id}


@app.get("/reports")
def get_reports():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, task_type, title, content, created_at FROM queue WHERE task_type IN ('monitor_report', 'analytics') ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/", response_class=HTMLResponse)
def ui():
    return """<!DOCTYPE html>
<html>
<head>
<title>GhostDesk Marketing Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: monospace; background: #0d0d0d; color: #e0e0e0; padding: 20px; max-width: 900px; margin: 0 auto; }
  h1 { color: #7c3aed; margin-bottom: 20px; font-size: 1.4rem; }
  h2 { color: #a78bfa; font-size: 1rem; margin: 20px 0 10px; }
  #chat { display: flex; gap: 10px; margin-bottom: 20px; }
  #msg { flex: 1; background: #1a1a1a; border: 1px solid #333; color: #e0e0e0; padding: 10px; font-family: monospace; border-radius: 4px; }
  button { background: #7c3aed; color: white; border: none; padding: 10px 18px; cursor: pointer; border-radius: 4px; font-family: monospace; }
  button:hover { background: #6d28d9; }
  button.danger { background: #b91c1c; }
  button.success { background: #15803d; }
  #response { background: #1a1a1a; border: 1px solid #333; padding: 15px; border-radius: 4px; white-space: pre-wrap; min-height: 60px; margin-bottom: 20px; }
  .item { background: #1a1a1a; border: 1px solid #2a2a2a; padding: 12px; margin: 8px 0; border-radius: 4px; }
  .item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .item-type { color: #a78bfa; font-size: 0.8rem; }
  .item-content { font-size: 0.85rem; color: #aaa; max-height: 120px; overflow-y: auto; white-space: pre-wrap; }
  .actions { display: flex; gap: 8px; margin-top: 10px; }
  .badge { display: inline-block; background: #2a2a2a; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
</style>
</head>
<body>
<h1>⚡ GhostDesk Marketing Agent</h1>

<div id="chat">
  <input id="msg" type="text" placeholder="Ask the agent anything... (e.g. 'draft a Reddit post about GhostDesk for devs')" onkeydown="if(event.key==='Enter') send()">
  <button onclick="send()">Send</button>
</div>
<div id="response">Agent response will appear here...</div>

<div style="display:flex; gap:10px; margin-bottom:10px;">
  <button onclick="loadQueue()">Refresh Queue</button>
  <button onclick="loadReports()">View Reports</button>
</div>

<h2>Approval Queue</h2>
<div id="queue">Loading...</div>

<h2>Reports</h2>
<div id="reports"></div>

<script>
async function send() {
  const msg = document.getElementById('msg').value.trim();
  if (!msg) return;
  document.getElementById('response').textContent = 'Thinking...';
  document.getElementById('msg').value = '';
  const res = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})});
  const data = await res.json();
  document.getElementById('response').textContent = data.reply;
  loadQueue();
}

async function loadQueue() {
  const res = await fetch('/queue');
  const items = await res.json();
  const el = document.getElementById('queue');
  if (!items.length) { el.innerHTML = '<p style="color:#555">No pending items</p>'; return; }
  el.innerHTML = items.map(i => `
    <div class="item">
      <div class="item-header">
        <span>#${i.id} — <strong>${i.title || '(untitled)'}</strong></span>
        <span class="item-type badge">${i.task_type}</span>
      </div>
      <div class="item-content">${i.content.substring(0, 400)}${i.content.length > 400 ? '...' : ''}</div>
      <div class="actions">
        <button class="success" onclick="approve(${i.id})">✓ Approve & Post</button>
        <button class="danger" onclick="reject(${i.id})">✗ Reject</button>
      </div>
    </div>`).join('');
}

async function loadReports() {
  const res = await fetch('/reports');
  const items = await res.json();
  document.getElementById('reports').innerHTML = items.map(i => `
    <div class="item">
      <div class="item-header"><strong>${i.title}</strong><span class="badge">${i.created_at}</span></div>
      <div class="item-content">${i.content.substring(0, 600)}...</div>
    </div>`).join('') || '<p style="color:#555">No reports yet</p>';
}

async function approve(id) {
  await fetch('/approve/' + id, {method:'POST'});
  loadQueue();
}

async function reject(id) {
  await fetch('/reject/' + id, {method:'POST'});
  loadQueue();
}

loadQueue();
</script>
</body>
</html>"""
