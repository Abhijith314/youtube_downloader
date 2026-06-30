
let _sseSource = null;

function startSSE() {
  if (_sseSource) _sseSource.close();
  _sseSource = new EventSource("/api/progress");
  _sseSource.onmessage = e => renderQueue(JSON.parse(e.data));
}

function refreshQueue() {
  fetch("/api/status").then(r => r.json()).then(renderQueue);
}

function renderQueue(tasks) {
  const list = document.getElementById("queueList");
  if (!tasks || !tasks.length) {
    list.innerHTML = '<div class="empty-state">No downloads yet</div>';
    return;
  }
  list.innerHTML = "";
  tasks.slice().reverse().forEach(t => {
    const icons = { queued:"⏳", downloading:"⬇", processing:"⚙", done:"✅", error:"❌" };
    const sub   = t.status === "downloading" ? t.progress + "% — " + t.speed_kbps + " KB/s"
                : t.status === "error"       ? (t.error || "Failed")
                : t.status;
    const item  = document.createElement("div");
    item.className = "queue-item";
    item.innerHTML =
      "<span class='q-icon'>" + (icons[t.status] || "⏳") + "</span>"
    + "<div class='q-info'>"
    +   "<div class='q-title'>" + esc(t.metadata && t.metadata.title ? t.metadata.title : (t.url || "Track")) + "</div>"
    +   "<div class='q-sub'>" + esc((t.metadata && t.metadata.artist) || "") + " " + (t.mode||"") + " " + (t.quality||"") + "</div>"
    + "</div>"
    + "<div class='q-bar-wrap'>"
    +   "<div class='q-bar'><div class='q-bar-fill' style='width:" + (t.progress || 0) + "%'></div></div>"
    +   "<div class='q-sub' style='margin-top:4px'>" + sub + "</div>"
    + "</div>"
    + "<span class='q-status " + t.status + "'>" + t.status + "</span>";
    list.appendChild(item);
  });
}

function clearDone() {
  fetch("/api/status").then(r => r.json()).then(tasks => {
    renderQueue(tasks.filter(t => !["done","error"].includes(t.status)));
  });
}

function esc(str) {
  return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

startSSE();
setInterval(() => {
  if (document.getElementById("tab-queue").classList.contains("active")) refreshQueue();
}, 2000);
