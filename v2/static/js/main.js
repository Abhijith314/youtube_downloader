
let currentInfo = null;
let selectedFmt = { type: null, format_id: null, quality: null };

// Tab navigation
document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    link.classList.add("active");
    document.getElementById("tab-" + tab).classList.add("active");
    if (tab === "queue") refreshQueue();
  });
});

// URL badge auto-detect
document.getElementById("urlInput").addEventListener("input", function () {
  const v = this.value;
  const badge = document.getElementById("urlBadge");
  if (/open\.spotify\.com\/playlist/.test(v))    badge.textContent = "🟢 Spotify Playlist";
  else if (/open\.spotify\.com\/album/.test(v))  badge.textContent = "🟢 Spotify Album";
  else if (/open\.spotify\.com\/track/.test(v))  badge.textContent = "🟢 Spotify Track";
  else if (/music\.youtube\.com.*list=/.test(v)) badge.textContent = "🎵 YTMusic Playlist";
  else if (/music\.youtube\.com/.test(v))        badge.textContent = "🎵 YTMusic Track";
  else if (/youtube\.com.*list=/.test(v))        badge.textContent = "🎥 YT Playlist";
  else if (/youtube\.com|youtu\.be/.test(v))     badge.textContent = "🎥 YouTube";
  else                                            badge.textContent = "🔗 URL";
});

// Fetch Info
async function fetchInfo() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) return;
  hide("singleCard"); hide("playlistCard"); hide("errorBanner");
  show("loadingSpinner");
  document.getElementById("fetchBtn").disabled = true;
  try {
    const resp = await fetch("/api/fetch-info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await resp.json();
    hide("loadingSpinner");
    document.getElementById("fetchBtn").disabled = false;
    if (data.error) { showError(data.error); return; }
    currentInfo = data;
    if (data.type === "single") renderSingle(data);
    else renderPlaylist(data);
  } catch (err) {
    hide("loadingSpinner");
    document.getElementById("fetchBtn").disabled = false;
    showError("Network error: " + err.message);
  }
}

document.getElementById("urlInput").addEventListener("keydown", e => {
  if (e.key === "Enter") fetchInfo();
});

// Render single video/track
function renderSingle(data) {
  document.getElementById("mediaThumb").src            = data.thumbnail || data.cover_url || "";
  document.getElementById("mediaTitle").textContent    = data.title    || "Unknown";
  document.getElementById("mediaChannel").textContent  = data.channel  || data.artist || "";
  const dur = data.duration || (data.duration_ms ? data.duration_ms / 1000 : 0);
  document.getElementById("mediaDuration").textContent = dur ? "⏱ " + fmtDur(dur) : "";

  const videoSection = document.getElementById("videoFormats");
  const videoGrid    = document.getElementById("videoGrid");
  videoGrid.innerHTML = "";
  if (data.source === "youtube" && data.video_formats && data.video_formats.length) {
    videoSection.classList.remove("hidden");
    data.video_formats.forEach(f => videoGrid.appendChild(makeChip(f.quality, f.size_mb, "video", f.format_id)));
  } else {
    videoSection.classList.add("hidden");
  }

  const audioGrid = document.getElementById("audioGrid");
  audioGrid.innerHTML = "";
  if (data.audio_formats && data.audio_formats.length) {
    data.audio_formats.forEach(f => audioGrid.appendChild(makeChip(f.quality, f.size_mb, "audio", f.format_id)));
    const chips = audioGrid.querySelectorAll(".format-chip");
    if (chips.length) chips[chips.length - 1].click();
  } else {
    const durSec = data.duration || (data.duration_ms ? data.duration_ms / 1000 : 180);
    [320, 256, 192, 128].forEach(kbps => {
      audioGrid.appendChild(makeChip(kbps + " kbps", calcSizeMB(kbps, durSec), "audio", String(kbps)));
    });
    audioGrid.querySelectorAll(".format-chip")[0].click();
  }
  show("singleCard");
}

function makeChip(quality, size_mb, type, format_id) {
  const chip = document.createElement("div");
  chip.className = "format-chip";
  chip.dataset.type     = type;
  chip.dataset.formatId = format_id;
  chip.dataset.quality  = quality;
  chip.innerHTML = "<span class='chip-q'>" + quality + "</span>"
                 + "<span class='chip-s'>" + (size_mb ? size_mb + " MB" : "~") + "</span>";
  chip.addEventListener("click", () => {
    document.querySelectorAll(".format-chip[data-type='" + type + "']")
            .forEach(c => c.classList.remove("selected"));
    chip.classList.add("selected");
    selectedFmt = { type, format_id, quality };
  });
  return chip;
}

// Download single
async function downloadSingle() {
  if (!selectedFmt.type) { alert("Select a format first."); return; }
  const task = {
    url      : currentInfo.url || "",
    source   : currentInfo.source,
    mode     : selectedFmt.type,
    quality  : selectedFmt.quality.replace(" kbps", "").trim(),
    format_id: selectedFmt.format_id,
    metadata : {
      title    : currentInfo.title    || "",
      artist   : currentInfo.channel  || currentInfo.artist || "",
      album    : currentInfo.album    || "",
      cover_url: currentInfo.thumbnail || currentInfo.cover_url || "",
    },
  };
  await fetch("/api/download-single", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(task),
  });
  document.querySelector('.nav-link[data-tab="queue"]').click();
}

// Playlist
let plTracks = [];

function renderPlaylist(data) {
  document.getElementById("plCover").src        = data.cover_url || "";
  document.getElementById("plName").textContent  = data.name     || "Playlist";
  document.getElementById("plCount").textContent = data.tracks.length + " tracks";
  plTracks = data.tracks.map((t, i) => ({ ...t, index: i, selected: true }));
  renderTrackList();
  show("playlistCard");
}

function renderTrackList() {
  const list    = document.getElementById("trackList");
  list.innerHTML = "";
  const mode    = document.querySelector('input[name="plMode"]:checked').value;
  const quality = parseInt(document.getElementById("plQuality").value);
  plTracks.forEach((t, i) => {
    const dur = t.duration_ms ? t.duration_ms / 1000 : 0;
    const sz  = calcSizeMB(mode === "audio" ? quality : 2000, dur);
    const row = document.createElement("div");
    row.className = "track-item" + (t.selected ? " selected" : "");
    row.innerHTML =
      "<input type='checkbox'" + (t.selected ? " checked" : "") + " onchange='toggleTrack(" + i + ",this.checked)'>"
    + "<span class='track-num'>" + (i + 1) + "</span>"
    + "<div class='track-info'>"
    +   "<div class='track-title'>" + esc(t.title) + "</div>"
    +   "<div class='track-artist'>" + esc(t.artist || t.channel || "") + "</div>"
    + "</div>"
    + "<span class='track-dur'>" + (dur ? fmtDur(dur) : "-") + "</span>"
    + "<span class='track-size'>" + (sz ? sz + " MB" : "-") + "</span>";
    row.addEventListener("click", e => {
      if (e.target.type !== "checkbox") {
        const cb = row.querySelector("input[type=checkbox]");
        cb.checked = !cb.checked;
        toggleTrack(i, cb.checked);
      }
    });
    list.appendChild(row);
  });
  updatePlFooter();
}

function toggleTrack(i, checked) {
  plTracks[i].selected = checked;
  document.querySelectorAll(".track-item")[i].classList.toggle("selected", checked);
  updatePlFooter();
}

function selectAll(val) { plTracks.forEach(t => t.selected = val); renderTrackList(); }

function updatePlFooter() {
  const sel     = plTracks.filter(t => t.selected);
  const quality = parseInt(document.getElementById("plQuality").value);
  const mode    = document.querySelector('input[name="plMode"]:checked').value;
  let totalMB   = 0;
  sel.forEach(t => {
    const sz = calcSizeMB(mode === "audio" ? quality : 2000, t.duration_ms ? t.duration_ms / 1000 : 0);
    if (sz) totalMB += sz;
  });
  document.getElementById("plSelectedCount").textContent = sel.length + " selected";
  document.getElementById("plTotalSize").textContent = totalMB > 0 ? "Total: ~" + totalMB.toFixed(1) + " MB" : "";
}

document.querySelectorAll('input[name="plMode"]').forEach(r => r.addEventListener("change", renderTrackList));
document.getElementById("plQuality").addEventListener("change", renderTrackList);

async function downloadPlaylist() {
  const selected = plTracks.filter(t => t.selected);
  if (!selected.length) { alert("Select at least one track."); return; }
  await fetch("/api/download-playlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tracks : selected,
      source : currentInfo.source,
      mode   : document.querySelector('input[name="plMode"]:checked').value,
      quality: document.getElementById("plQuality").value,
    }),
  });
  document.querySelector('.nav-link[data-tab="queue"]').click();
}

// Helpers
function fmtDur(s) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60);
  return m + ":" + String(sec).padStart(2, "0");
}
function calcSizeMB(kbps, dur) {
  if (!kbps || !dur) return null;
  return parseFloat(((kbps * 1000 * dur) / 8 / 1048576).toFixed(1));
}
function esc(str) {
  return String(str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function show(id) { const el = document.getElementById(id); if (el) el.classList.remove("hidden"); }
function hide(id) { const el = document.getElementById(id); if (el) el.classList.add("hidden"); }
function showError(msg) {
  const el = document.getElementById("errorBanner");
  el.textContent = "⚠ " + msg;
  el.classList.remove("hidden");
}
