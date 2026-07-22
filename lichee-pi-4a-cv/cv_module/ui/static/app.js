const $ = (id) => document.getElementById(id);

let sourceMode = "file";
let confidenceTimer = null;
let confidenceDragging = false;
let pipelineRunning = false;
let pipelinePaused = false;
let playToggleLock = false;

function confidenceFromSlider() {
  return Number($("confidenceSlider").value) / 100;
}

function setConfidenceUi(value) {
  const pct = Math.round(value * 100);
  $("confidenceSlider").value = String(pct);
  $("confidenceValue").textContent = `${pct}%`;
}

async function applyConfidence() {
  const threshold = confidenceFromSlider();
  await api("/config", { method: "POST", body: JSON.stringify({ confidence_threshold: threshold }) });
}

function scheduleConfidenceUpdate() {
  if (confidenceTimer) clearTimeout(confidenceTimer);
  confidenceTimer = setTimeout(() => applyConfidence().catch(console.error), 250);
}

const CLASS_LABELS = {
  person: "Человек",
  vehicle: "Транспорт",
  fire: "Огонь",
  smoke: "Дым",
  water: "Вода",
  no_helmet: "Без каски",
};

function formatEventTime(iso) {
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso || "—";
  }
}

function formatConfidence(value) {
  const pct = Math.round((Number(value) || 0) * 100);
  return `${pct}%`;
}

async function api(path, opts = {}) {
  const h = { ...(opts.headers || {}) };
  if (opts.body && typeof opts.body === "string" && !h["Content-Type"]) h["Content-Type"] = "application/json";
  const r = await fetch(path, { ...opts, headers: h });
  if (!r.ok) throw new Error(await r.text() || r.statusText);
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}

function defaultCameraId() {
  return sourceMode === "external_camera" ? 1 : 0;
}

function mapSourceConfig() {
  if (sourceMode === "file") return { input_source: "file" };
  const input_source = sourceMode === "external_camera" ? "external" : "builtin";
  const id = Number($("cameraSelect").value);
  return {
    input_source,
    camera_id: Number.isFinite(id) ? id : defaultCameraId(),
  };
}

function showSourcePanel() {
  $("panelFile").hidden = sourceMode !== "file";
  $("panelCamera").hidden = sourceMode === "file";
  document.querySelectorAll("#sourceSubmenu button").forEach((b) => {
    b.classList.toggle("active", b.dataset.source === sourceMode);
  });
  $("renderGroup").hidden = sourceMode !== "file";
}

async function loadVideos() {
  const data = await api("/videos");
  const sel = $("videoSelect");
  sel.innerHTML = data.videos.length
    ? data.videos.map((v) => `<option value="${v.path}">${v.name}</option>`).join("")
    : '<option value="">Нет видео в videos/</option>';
}

function fillCameraSelect() {
  const sel = $("cameraSelect");
  const defaultId = defaultCameraId();
  const ids = [0, 1, 2];
  sel.innerHTML = ids.map((id) => `<option value="${id}">Камера ${id}</option>`).join("");
  sel.value = String(defaultId);
}

async function refreshCameras() {
  try {
    const data = await api("/cameras");
    if (!data.cameras.length) return;
    const sel = $("cameraSelect");
    const defaultId = defaultCameraId();
    sel.innerHTML = data.cameras.map((c) => `<option value="${c.id}">${c.label}</option>`).join("");
    const hasDefault = data.cameras.some((c) => c.id === defaultId);
    sel.value = String(hasDefault ? defaultId : data.cameras[0].id);
  } catch (e) {
    console.warn("camera probe failed", e);
  }
}

function updatePlayUi(state) {
  pipelineRunning = state === "running";
  pipelinePaused = state === "paused";
  const btn = $("btnTogglePlay");
  btn.textContent = pipelineRunning ? "Пауза" : "Старт";
  btn.title = pipelineRunning ? "Пауза (Space)" : "Старт (Space)";
  btn.classList.toggle("primary", !pipelineRunning);
  btn.setAttribute("aria-pressed", pipelineRunning ? "true" : "false");
}

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

async function togglePlay() {
  if (playToggleLock) return;
  playToggleLock = true;
  try {
    if (pipelineRunning) await pauseProcessing();
    else if (pipelinePaused) await resumeProcessing();
    else await startProcessing();
  } catch (e) {
    alert(e.message);
  } finally {
    playToggleLock = false;
  }
}

async function refreshStatus() {
  const s = await api("/status");
  $("fps").textContent = s.fps ?? 0;
  $("statusBadge").textContent = s.state;
  $("statusBadge").className = `badge ${s.state}`;
  updatePlayUi(s.state);
  if (!confidenceDragging && s.confidence_threshold != null) {
    setConfidenceUi(s.confidence_threshold);
  }
  if (s.error) {
    $("errorBox").hidden = false;
    $("errorBox").textContent = s.error;
  } else {
    $("errorBox").hidden = true;
  }
}

async function refreshFrame() {
  const r = await fetch(`/frame/latest?t=${Date.now()}`);
  if (!r.ok) return;
  $("videoFrame").src = URL.createObjectURL(await r.blob());
  $("videoFrame").style.display = "block";
  $("placeholder").style.display = "none";
}

async function refreshEvents() {
  const data = await api("/events?limit=50");
  $("eventsList").innerHTML = data.events.map((e) => {
    const label = CLASS_LABELS[e.object_class] || e.object_class;
    const conf = formatConfidence(e.confidence);
    const fps = e.fps != null ? Number(e.fps).toFixed(1) : "—";
    const ms = e.detection_ms != null ? `${Math.round(e.detection_ms)} ms` : "—";
    const time = formatEventTime(e.timestamp);
    return `
    <li>
      <div class="event-title">${label}</div>
      <div class="event-stats">
        <span>Точность <strong>${conf}</strong></span>
        <span>FPS <strong>${fps}</strong></span>
        <span>${time}</span>
        <span>${ms}</span>
      </div>
      <div class="event-meta">${e.id}</div>
    </li>`;
  }).join("");
}

async function startProcessing() {
  const cfg = mapSourceConfig();
  if (sourceMode === "file") {
    const path = $("videoSelect").value;
    if (!path) return alert("Выберите видеофайл");
    cfg.video_path = path;
  }
  await api("/stop", { method: "POST" });
  cfg.confidence_threshold = confidenceFromSlider();
  await api("/config", { method: "POST", body: JSON.stringify(cfg) });
  await api("/start", { method: "POST" });
  await refreshStatus();
}

async function pauseProcessing() {
  await api("/pause", { method: "POST" });
  await refreshStatus();
}

async function resumeProcessing() {
  await api("/config", {
    method: "POST",
    body: JSON.stringify({ confidence_threshold: confidenceFromSlider() }),
  });
  await api("/start", { method: "POST" });
  await refreshStatus();
}

async function stopProcessing() {
  await api("/stop", { method: "POST" });
  await refreshStatus();
}

async function saveRenderJson(report) {
  const json = JSON.stringify(report, null, 2);
  const base = (report.video_name || "video").replace(/\.[^.]+$/, "");
  const suggestedName = `${base}_render.json`;

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName,
        types: [{ description: "JSON", accept: { "application/json": [".json"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(json);
      await writable.close();
      return;
    } catch (err) {
      if (err?.name === "AbortError") return;
    }
  }

  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = suggestedName;
  link.click();
  URL.revokeObjectURL(url);
}

async function runRender() {
  if (sourceMode !== "file") {
    alert("Рендер доступен только для видеофайла");
    return;
  }
  const videoPath = $("videoSelect").value;
  if (!videoPath) {
    alert("Выберите видеофайл");
    return;
  }
  const btn = $("btnRender");
  btn.disabled = true;
  btn.textContent = "Рендер…";
  $("errorBox").hidden = false;
  $("errorBox").textContent = "Рендер: обработка всего видео, подождите…";
  try {
    if (pipelineRunning) await pauseProcessing();
    const report = await api("/render", {
      method: "POST",
      body: JSON.stringify({
        video_path: videoPath,
        confidence_threshold: confidenceFromSlider(),
      }),
    });
    $("errorBox").hidden = true;
    await saveRenderJson(report);
    alert(`Готово: ${report.summary.total_detections} детекций, ${report.video.frame_count} кадров`);
    await refreshStatus();
  } catch (e) {
    $("errorBox").hidden = false;
    $("errorBox").textContent = e.message;
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Рендер";
  }
}

$("btnSourceMenu").onclick = () => $("sourceSubmenu").classList.toggle("open");
document.querySelectorAll("#sourceSubmenu button").forEach((btn) => {
  btn.onclick = () => {
    sourceMode = btn.dataset.source;
    $("sourceSubmenu").classList.remove("open");
    showSourcePanel();
    if (sourceMode !== "file") fillCameraSelect();
  };
});

$("btnRefreshVideos").onclick = () => loadVideos().catch(alert);
$("btnRefreshCameras").onclick = () => refreshCameras().catch(alert);
$("videoSelect").onchange = () => {
  if (pipelinePaused || pipelineRunning) stopProcessing().catch(console.error);
};
$("cameraSelect").onchange = () => {
  if (pipelinePaused || pipelineRunning) stopProcessing().catch(console.error);
};
$("btnRender").onclick = () => runRender().catch(alert);

const confSlider = $("confidenceSlider");
confSlider.oninput = () => {
  $("confidenceValue").textContent = `${confSlider.value}%`;
  scheduleConfidenceUpdate();
};
confSlider.onpointerdown = () => { confidenceDragging = true; };
confSlider.onpointerup = () => {
  confidenceDragging = false;
  applyConfidence().catch(console.error);
};

$("btnTogglePlay").onclick = () => togglePlay();
$("btnEvents").onclick = () => $("eventsDrawer").classList.add("open");
$("btnCloseEvents").onclick = () => $("eventsDrawer").classList.remove("open");

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.altKey && e.code === "KeyR") {
    if (isTypingTarget(e.target)) return;
    e.preventDefault();
    if (!$("renderGroup").hidden && !$("btnRender").disabled) runRender().catch(alert);
    return;
  }
  if (e.code !== "Space" || e.repeat) return;
  if (isTypingTarget(e.target)) return;
  e.preventDefault();
  togglePlay();
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".dropdown")) $("sourceSubmenu").classList.remove("open");
});

showSourcePanel();
loadVideos().catch(console.error);
setInterval(refreshStatus, 800);
setInterval(refreshFrame, 150);
setInterval(refreshEvents, 2000);
refreshStatus();
