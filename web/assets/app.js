(() => {
  const params = new URLSearchParams(location.search);
  const mode = params.get("mode") === "student" ? "student" : "teacher";
  const isTeacher = mode === "teacher";
  const tenantFromUrl = String(params.get("t") || params.get("tenant") || "").trim();
  const clientId = "c_" + Math.random().toString(36).slice(2, 10);
  const logical = { w: 1600, h: 900 };

  const els = {
    courseBtn: document.getElementById("course-btn"),
    prevWbBtn: document.getElementById("prev-wb-btn"),
    nextWbBtn: document.getElementById("next-wb-btn"),
    wbTitle: document.getElementById("wb-title"),
    teacherTools: document.getElementById("teacher-tools"),
    colorInput: document.getElementById("color-input"),
    colorPresets: document.getElementById("color-presets"),
    sizeInput: document.getElementById("size-input"),
    undoBtn: document.getElementById("undo-btn"),
    clearBtn: document.getElementById("clear-btn"),
    zoomOutBtn: document.getElementById("zoom-out-btn"),
    zoomInBtn: document.getElementById("zoom-in-btn"),
    zoomLabel: document.getElementById("zoom-label"),
    burgerBtn: document.getElementById("burger-btn"),
    burgerMenu: document.getElementById("burger-menu"),
    shareStudentBtn: document.getElementById("share-student-btn"),
    shareTeacherBtn: document.getElementById("share-teacher-btn"),
    exportPngBtn: document.getElementById("export-png-btn"),
    exportPdfBtn: document.getElementById("export-pdf-btn"),
    exportWbBtn: document.getElementById("export-wb-btn"),
    importWbBtn: document.getElementById("import-wb-btn"),
    llmConfigBtn: document.getElementById("llm-config-btn"),
    importWbInput: document.getElementById("import-wb-input"),
    resetViewBtn: document.getElementById("reset-view-btn"),
    stage: document.getElementById("board-stage"),
    canvas: document.getElementById("board-canvas"),
    hotspotLayer: document.getElementById("hotspot-layer"),
    supervisionChip: document.getElementById("supervision-chip"),
    imageActions: document.getElementById("image-actions"),
    imageDuplicateBtn: document.getElementById("image-duplicate-btn"),
    imageDeleteBtn: document.getElementById("image-delete-btn"),
    courseDialog: document.getElementById("course-dialog"),
    courseList: document.getElementById("course-list"),
    wbList: document.getElementById("wb-list"),
    courseCreateBtn: document.getElementById("course-create-btn"),
    courseRenameBtn: document.getElementById("course-rename-btn"),
    courseDuplicateBtn: document.getElementById("course-duplicate-btn"),
    coursePdfsBtn: document.getElementById("course-pdfs-btn"),
    courseDeleteBtn: document.getElementById("course-delete-btn"),
    wbCreateBtn: document.getElementById("wb-create-btn"),
    wbRenameBtn: document.getElementById("wb-rename-btn"),
    wbDuplicateBtn: document.getElementById("wb-duplicate-btn"),
    wbCopyToCourseBtn: document.getElementById("wb-copy-to-course-btn"),
    wbDeleteBtn: document.getElementById("wb-delete-btn"),
    hotspotDialog: document.getElementById("hotspot-dialog"),
    hotspotTitle: document.getElementById("hotspot-title"),
    hotspotName: document.getElementById("hotspot-name"),
    hotspotColor: document.getElementById("hotspot-color"),
    hotspotHtml: document.getElementById("hotspot-html"),
    hotspotSaveBtn: document.getElementById("hotspot-save-btn"),
    hotspotDeleteBtn: document.getElementById("hotspot-delete-btn"),
    hotspotCancelBtn: document.getElementById("hotspot-cancel-btn"),
    contentDialog: document.getElementById("content-dialog"),
    contentTitle: document.getElementById("content-title"),
    contentHtml: document.getElementById("content-html"),
    chatWrap: document.getElementById("hotspot-chat-wrap"),
    chatQueueStatus: document.getElementById("chat-queue-status"),
    chatMessages: document.getElementById("chat-messages"),
    chatInput: document.getElementById("chat-input"),
    chatSendBtn: document.getElementById("chat-send-btn"),
    chatReleaseBtn: document.getElementById("chat-release-btn"),
    shareDialog: document.getElementById("share-dialog"),
    shareTitle: document.getElementById("share-title"),
    shareUrl: document.getElementById("share-url"),
    shareQr: document.getElementById("share-qr"),
    shareCopyBtn: document.getElementById("share-copy-btn"),
    shareCloseBtn: document.getElementById("share-close-btn"),
    pdfDialog: document.getElementById("pdf-dialog"),
    pdfStatus: document.getElementById("pdf-status"),
    pdfDogLoader: document.getElementById("pdf-dog-loader"),
    pdfList: document.getElementById("pdf-list"),
    pdfUploadInput: document.getElementById("pdf-upload-input"),
    pdfUploadBtn: document.getElementById("pdf-upload-btn"),
    pdfRefreshBtn: document.getElementById("pdf-refresh-btn"),
    pdfCloseBtn: document.getElementById("pdf-close-btn"),
    supervisionDialog: document.getElementById("supervision-dialog"),
    supervisionSummary: document.getElementById("supervision-summary"),
    supervisionQueue: document.getElementById("supervision-queue"),
    supervisionActive: document.getElementById("supervision-active"),
    llmDialog: document.getElementById("llm-dialog"),
    llmProviderSelect: document.getElementById("llm-provider-select"),
    llmApertusModelInput: document.getElementById("llm-apertus-model-input"),
    llmSaveBtn: document.getElementById("llm-save-btn"),
    llmCloseBtn: document.getElementById("llm-close-btn"),
    passwordDialog: document.getElementById("password-dialog"),
    pwdCurrentInput: document.getElementById("pwd-current-input"),
    pwdNewInput: document.getElementById("pwd-new-input"),
    pwdConfirmInput: document.getElementById("pwd-confirm-input"),
    pwdSaveBtn: document.getElementById("pwd-save-btn"),
    pwdCloseBtn: document.getElementById("pwd-close-btn"),
    usersDialog: document.getElementById("users-dialog"),
    usersList: document.getElementById("users-list"),
    usersRefreshBtn: document.getElementById("users-refresh-btn"),
    newUserNameInput: document.getElementById("new-user-name-input"),
    newUserPasswordInput: document.getElementById("new-user-password-input"),
    newUserAdminInput: document.getElementById("new-user-admin-input"),
    usersCreateBtn: document.getElementById("users-create-btn"),
    usersCloseBtn: document.getElementById("users-close-btn"),
    barkAudio: document.getElementById("bark-audio"),
    status: document.getElementById("status"),
  };

  const state = {
    shareBaseUrl: location.origin,
    tenantKey: tenantFromUrl,
    catalog: null,
    activeBoard: null,
    ws: null,
    users: 0,
    students: 0,
    tool: "pen",
    color: "#1a1a1a",
    size: 3,
    zoom: 1,
    panX: 0,
    panY: 0,
    drawing: false,
    drawPoints: [],
    panning: false,
    panStart: null,
    selectedImageId: null,
    imageDrag: null,
    selectedCourseId: null,
    selectedWbId: null,
    editingHotspot: null,
    openHotspot: null,
    chat: {
      studentName: "",
      sessionId: "",
      messages: [],
      pending: false,
      queue: { active: false, position: 0, queueLength: 0 },
      pollTimer: null,
    },
    supervision: {
      queueLength: 0,
      activeCount: 0,
      queue: [],
      active: [],
      promptsSession: 0,
      promptsTotal: 0,
    },
    pdfs: {
      files: [],
      indexing: { running: false, error: "" },
      currentCourseId: "",
    },
    llm: {
      provider: "local",
      apertusModel: "",
    },
    auth: {
      authenticated: false,
      user: null,
      users: [],
    },
    pinch: null,
    imageCache: {},
  };

  function ensureLlmUi() {
    const topRight = document.querySelector(".top-right");

    if (!els.llmConfigBtn && topRight) {
      const btn = document.createElement("button");
      btn.id = "llm-config-btn";
      btn.className = "btn";
      btn.textContent = "IA: Qwen";
      topRight.insertBefore(btn, els.burgerBtn || null);
      els.llmConfigBtn = btn;
    }
    if (topRight && els.llmConfigBtn && els.llmConfigBtn.parentElement !== topRight) {
      els.llmConfigBtn.className = "btn";
      topRight.insertBefore(els.llmConfigBtn, els.burgerBtn || null);
    }

    if (!els.llmDialog) {
      const dlg = document.createElement("dialog");
      dlg.id = "llm-dialog";
      dlg.className = "dialog";
      dlg.innerHTML = `
        <h3>Configuration IA</h3>
        <label>Provider
          <select id="llm-provider-select">
            <option value="local">Qwen local</option>
            <option value="apertus">Apertus</option>
          </select>
        </label>
        <label>Apertus model
          <input id="llm-apertus-model-input" type="text" />
        </label>
        <div class="actions">
          <button id="llm-save-btn" class="btn primary">Sauver</button>
          <button id="llm-close-btn" class="btn">Fermer</button>
        </div>
      `;
      document.body.appendChild(dlg);
      els.llmDialog = dlg;
      els.llmProviderSelect = dlg.querySelector("#llm-provider-select");
      els.llmApertusModelInput = dlg.querySelector("#llm-apertus-model-input");
      els.llmSaveBtn = dlg.querySelector("#llm-save-btn");
      els.llmCloseBtn = dlg.querySelector("#llm-close-btn");
    }
  }

  function setStatus(msg) {
    const roleTxt = isTeacher ? "Prof" : "Consultation";
    const wb = state.activeBoard ? state.activeBoard.name : "-";
    els.status.textContent = `${roleTxt} | ${state.users} connectés | ${wb} | ${msg}`;
  }

  function ensureChatIdentity() {
    let sid = sessionStorage.getItem("maxboard_chat_session_id") || "";
    if (!sid) {
      sid = `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      sessionStorage.setItem("maxboard_chat_session_id", sid);
    }
    state.chat.sessionId = sid;
    let studentName = sessionStorage.getItem("maxboard_student_name") || "";
    if (!studentName) {
      const asked = prompt("Entrez votre nom pour le chat :", "");
      if (!asked) return false;
      studentName = asked.trim();
      if (!studentName) return false;
      sessionStorage.setItem("maxboard_student_name", studentName);
    }
    state.chat.studentName = studentName;
    return true;
  }

  function escapeHtml(input) {
    return String(input || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function safeLinkHref(rawHref) {
    const href = String(rawHref || "").trim();
    if (/^https?:\/\//i.test(href) || /^mailto:/i.test(href)) return href;
    return "#";
  }

  function renderMarkdownLite(input) {
    let text = escapeHtml(input).replace(/\r\n?/g, "\n");

    const blockTokens = [];
    text = text.replace(/```([\s\S]*?)```/g, (_m, code) => {
      const token = `@@MD_BLOCK_${blockTokens.length}@@`;
      blockTokens.push(`<pre class="chat-md-code"><code>${code}</code></pre>`);
      return token;
    });

    const inlineTokens = [];
    text = text.replace(/`([^`\n]+)`/g, (_m, code) => {
      const token = `@@MD_INLINE_${inlineTokens.length}@@`;
      inlineTokens.push(`<code class="chat-md-inline-code">${code}</code>`);
      return token;
    });

    text = text.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label, href) => {
      const safeHref = safeLinkHref(href);
      return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/__([^_]+)__/g, "<strong>$1</strong>");
    text = text.replace(/(^|[^\*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
    text = text.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, "$1<em>$2</em>");
    text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");
    text = text.replace(/\n/g, "<br>");

    text = text.replace(/@@MD_INLINE_(\d+)@@/g, (_m, i) => inlineTokens[Number(i)] || "");
    text = text.replace(/@@MD_BLOCK_(\d+)@@/g, (_m, i) => blockTokens[Number(i)] || "");
    return text;
  }

  function renderChatMessages() {
    const box = els.chatMessages;
    box.innerHTML = "";
    (state.chat.messages || []).forEach((m) => {
      const el = document.createElement("div");
      el.className = `chat-msg ${m.role === "user" ? "user" : "assistant"}`;
      const body = document.createElement("div");
      body.className = "chat-msg-body";
      body.innerHTML = renderMarkdownLite(m.content || "");
      el.appendChild(body);
      if (m.role === "assistant" && Number.isFinite(Number(m.elapsedMs))) {
        const t = document.createElement("div");
        t.className = "chat-msg-time";
        const ms = Number(m.elapsedMs);
        t.textContent = ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`;
        el.appendChild(t);
      }
      box.appendChild(el);
    });
    box.scrollTop = box.scrollHeight;
  }

  async function animateAssistantText(text, mode = "word", elapsedMs = null) {
    const full = String(text || "");
    const msg = { role: "assistant", content: "", elapsedMs };
    state.chat.messages.push(msg);
    renderChatMessages();

    const units =
      mode === "char"
        ? Array.from(full)
        : full.split(/(\s+)/).filter((x) => x && x.length > 0);

    const delayMs = mode === "char" ? 12 : 42;
    const stride = mode === "char" ? 2 : 1;
    for (let i = 0; i < units.length; i += stride) {
      msg.content += units.slice(i, i + stride).join("");
      renderChatMessages();
      await new Promise((resolve) => window.setTimeout(resolve, delayMs));
    }
    if (msg.content !== full) {
      msg.content = full;
      renderChatMessages();
    }
  }

  function renderSupervisionChip() {
    if (!isTeacher) return;
    const q = Number(state.supervision.queueLength || 0);
    const students = Number(state.students || 0);
    const promptsSession = Number(state.supervision.promptsSession || 0);
    els.supervisionChip.textContent = `Étudiants ${students} | File ${q} | Prompts ${promptsSession}`;
    els.supervisionChip.classList.remove("hidden");
  }

  function renderSupervisionDialog() {
    const s = state.supervision || {};
    els.supervisionSummary.textContent = `Actifs IA: ${s.activeCount || 0} / 5 | Prompts session: ${s.promptsSession || 0} | Prompts total: ${s.promptsTotal || 0}`;
    const qList = (s.queue || []).map((x) => `${x.position}. ${x.name}`).join("\n") || "File vide.";
    const aList = (s.active || []).map((x) => `• ${x.name}`).join("\n") || "Aucune session active.";
    els.supervisionQueue.textContent = `File d'attente:\n${qList}`;
    els.supervisionActive.textContent = `Sessions actives:\n${aList}`;
  }

  function renderLlmConfigDialog() {
    if (!els.llmProviderSelect || !els.llmApertusModelInput) return;
    const cfg = state.llm || { provider: "local", apertusModel: "" };
    const provider = cfg.provider === "apertus" ? "apertus" : "local";
    els.llmProviderSelect.value = provider;
    els.llmApertusModelInput.value = cfg.apertusModel || "";
    updateLlmModelFieldState();
  }

  function renderLlmProviderButton() {
    if (!els.llmConfigBtn) return;
    const provider = state.llm && state.llm.provider === "apertus" ? "Apertus" : "Qwen";
    els.llmConfigBtn.textContent = `IA: ${provider}`;
  }

  function updateLlmModelFieldState() {
    if (!els.llmProviderSelect || !els.llmApertusModelInput) return;
    const provider = String(els.llmProviderSelect.value || "local");
    els.llmApertusModelInput.disabled = provider !== "apertus";
  }

  function renderUsersDialog() {
    if (!els.usersList) return;
    const users = Array.isArray(state.auth.users) ? state.auth.users : [];
    if (!users.length) {
      els.usersList.innerHTML = "<div class='list-item'>Aucun prof.</div>";
      return;
    }
    els.usersList.innerHTML = "";
    users
      .slice()
      .sort((a, b) => String(a.username || "").localeCompare(String(b.username || "")))
      .forEach((u) => {
        const row = document.createElement("div");
        row.className = "list-item";
        const role = u.isAdmin ? "admin" : "prof";
        row.textContent = `${u.username} (${role})`;

        const actions = document.createElement("div");
        actions.className = "actions";

        const resetBtn = document.createElement("button");
        resetBtn.className = "btn";
        resetBtn.textContent = "Reset mdp";
        resetBtn.onclick = async () => {
          const nextPwd = prompt(`Nouveau mot de passe pour ${u.username} ?`, "");
          if (!nextPwd) return;
          await api(`/api/auth/users/${encodeURIComponent(u.username)}/password`, {
            method: "POST",
            body: JSON.stringify({ newPassword: nextPwd }),
          });
          setStatus(`Mot de passe changé pour ${u.username}`);
        };
        actions.appendChild(resetBtn);

        const me = state.auth.user && String(state.auth.user.username || "") === String(u.username || "");
        if (!me) {
          const delBtn = document.createElement("button");
          delBtn.className = "btn danger";
          delBtn.textContent = "Supprimer";
          delBtn.onclick = async () => {
            if (!confirm(`Supprimer le compte ${u.username} ?`)) return;
            await api(`/api/auth/users/${encodeURIComponent(u.username)}`, { method: "DELETE" });
            await loadUsersForAdmin();
          };
          actions.appendChild(delBtn);
        }

        row.appendChild(actions);
        els.usersList.appendChild(row);
      });
  }

  async function loadUsersForAdmin() {
    if (!state.auth.user || !state.auth.user.isAdmin) return;
    const out = await api("/api/auth/users");
    state.auth.users = Array.isArray(out && out.users) ? out.users : [];
    renderUsersDialog();
  }

  function updateChatQueueStatus() {
    const q = state.chat.queue || { active: false, position: 0, queueLength: 0 };
    if (q.active) {
      els.chatQueueStatus.textContent = "Actif";
      return;
    }
    if (q.position > 0) {
      els.chatQueueStatus.textContent = `En file (#${q.position}/${q.queueLength})`;
      return;
    }
    els.chatQueueStatus.textContent = "Libre";
  }

  function setPdfLoader(isRunning) {
    els.pdfDogLoader.classList.toggle("hidden", !isRunning);
    if (!isRunning) return;
    try {
      els.barkAudio.currentTime = 0;
      els.barkAudio.pause();
    } catch (_err) {}
  }

  function playBarkShort() {
    try {
      els.barkAudio.currentTime = 0;
      const p = els.barkAudio.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
      window.setTimeout(() => {
        try {
          els.barkAudio.pause();
          els.barkAudio.currentTime = 0;
        } catch (_err) {}
      }, 2200);
    } catch (_err) {}
  }

  function refreshPresetColorUI() {
    const chips = els.colorPresets ? els.colorPresets.querySelectorAll(".color-chip") : [];
    chips.forEach((chip) => {
      const c = String(chip.dataset.color || "").toLowerCase();
      const active = c === String(state.color || "").toLowerCase();
      chip.classList.toggle("active", active);
      chip.style.background = c || "#1a1a1a";
    });
  }

  function api(path, opts = {}) {
    let url = String(path || "");
    if (url.startsWith("/api/") && state.tenantKey) {
      const hasQuery = url.includes("?");
      const hasTenant = /[?&](t|tenant)=/.test(url);
      if (!hasTenant) {
        url += `${hasQuery ? "&" : "?"}t=${encodeURIComponent(state.tenantKey)}`;
      }
    }
    return fetch(url, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      credentials: "same-origin",
      ...opts,
    }).then(async (r) => {
      if (!r.ok) {
        const txt = await r.text();
        let detail = txt;
        try {
          const payload = JSON.parse(txt || "{}");
          if (payload && payload.detail) detail = String(payload.detail);
        } catch (_err) {}
        throw new Error(detail || `HTTP ${r.status}`);
      }
      const ctype = r.headers.get("content-type") || "";
      if (ctype.includes("application/json")) return r.json();
      return r.blob();
    });
  }

  async function ensureTeacherAuth() {
    if (!isTeacher) return;
    while (true) {
      let me = null;
      try {
        me = await api("/api/auth/me");
      } catch (_err) {
        me = { authenticated: false };
      }
      if (me && me.authenticated) {
        state.auth.authenticated = true;
        state.auth.user = me.user || null;
        return;
      }
      const username = prompt("Connexion Prof - Nom d'utilisateur", "");
      if (!username) throw new Error("Connexion requise pour le mode Prof");
      const password = prompt("Connexion Prof - Mot de passe", "");
      if (!password) throw new Error("Connexion requise pour le mode Prof");
      try {
        const out = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
        state.auth.authenticated = Boolean(out && out.ok);
        state.auth.user = out && out.user ? out.user : null;
        return;
      } catch (e) {
        alert(`Connexion refusée: ${e.message}`);
      }
    }
  }

  function activeCourse() {
    if (!state.catalog) return null;
    return state.catalog.courses.find((c) => c.id === state.catalog.activeCourseId) || null;
  }

  function boardSummary(id) {
    return (state.catalog && state.catalog.whiteboards && state.catalog.whiteboards[id]) || null;
  }

  function courseById(id) {
    if (!state.catalog) return null;
    return state.catalog.courses.find((c) => c.id === id) || null;
  }

  function wbOrder() {
    const c = activeCourse();
    return c ? c.whiteboardOrder || [] : [];
  }

  function makeId(prefix) {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  }

  function chooseTargetCourseId(defaultCourseId) {
    const courses = (state.catalog && state.catalog.courses) || [];
    const candidates = courses.filter((c) => c.id !== defaultCourseId);
    if (!candidates.length) {
      alert("Aucun autre cours disponible.");
      return null;
    }
    const msg = [
      "Copier vers quel cours ?",
      "",
      ...candidates.map((c, i) => `${i + 1}. ${c.name}`),
      "",
      "Entrez le numéro du cours cible :",
    ].join("\n");
    const raw = prompt(msg, "1");
    if (!raw) return null;
    const idx = Number(raw) - 1;
    if (!Number.isFinite(idx) || idx < 0 || idx >= candidates.length) {
      alert("Choix invalide.");
      return null;
    }
    return candidates[idx].id;
  }

  function chooseTool(tool) {
    state.tool = tool;
    if (tool !== "image") {
      state.selectedImageId = null;
      state.imageDrag = null;
    }
    document.querySelectorAll(".tool").forEach((b) => {
      b.classList.toggle("active", b.dataset.tool === tool);
    });
    renderHotspots();
    render();
  }

  function resizeCanvas() {
    const rect = els.stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    els.canvas.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
    els.canvas.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
    render();
  }

  function toScreen(nx, ny) {
    const w = els.canvas.width;
    const h = els.canvas.height;
    return {
      x: nx * w * state.zoom + state.panX,
      y: ny * h * state.zoom + state.panY,
    };
  }

  function fromEvent(ev) {
    const rect = els.canvas.getBoundingClientRect();
    const cx = (ev.clientX - rect.left) * devicePixelRatio;
    const cy = (ev.clientY - rect.top) * devicePixelRatio;
    const nx = (cx - state.panX) / Math.max(1, els.canvas.width * state.zoom);
    const ny = (cy - state.panY) / Math.max(1, els.canvas.height * state.zoom);
    return {
      x: Math.min(1, Math.max(0, nx)),
      y: Math.min(1, Math.max(0, ny)),
    };
  }

  function drawStroke(ctx, s) {
    if (!s || !Array.isArray(s.points) || s.points.length < 1) return;
    if (s.tool === "watercolor") {
      drawWatercolorStroke(ctx, s);
      return;
    }
    ctx.save();
    ctx.globalCompositeOperation = s.tool === "eraser" ? "destination-out" : "source-over";
    ctx.strokeStyle = s.color || "#1a1a1a";
    ctx.lineWidth = Math.max(1, Number(s.size || 2) * state.zoom * devicePixelRatio);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const p0 = toScreen(s.points[0].x, s.points[0].y);
    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);
    for (let i = 1; i < s.points.length; i++) {
      const p = toScreen(s.points[i].x, s.points[i].y);
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
  }

  function drawWatercolorStroke(ctx, s) {
    const points = Array.isArray(s.points) ? s.points : [];
    if (points.length < 1) return;
    const passes = [
      { mul: 2.8, alpha: 0.08 },
      { mul: 1.9, alpha: 0.12 },
      { mul: 1.2, alpha: 0.16 },
    ];
    ctx.save();
    ctx.globalCompositeOperation = "source-over";
    ctx.strokeStyle = s.color || "#1a1a1a";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    passes.forEach((p) => {
      ctx.globalAlpha = p.alpha;
      ctx.lineWidth = Math.max(1, Number(s.size || 2) * p.mul * state.zoom * devicePixelRatio);
      const p0 = toScreen(points[0].x, points[0].y);
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      for (let i = 1; i < points.length; i++) {
        const pt = toScreen(points[i].x, points[i].y);
        ctx.lineTo(pt.x, pt.y);
      }
      ctx.stroke();
    });
    ctx.restore();
  }

  function drawImageItem(ctx, item, isSelected) {
    if (!item || !item.src) return;
    if (!state.imageCache[item.src]) {
      const img = new Image();
      img.onload = () => render();
      img.src = item.src;
      state.imageCache[item.src] = img;
    }
    const img = state.imageCache[item.src];
    if (!img || !img.complete) return;
    const topLeft = toScreen(item.x || 0, item.y || 0);
    const w = (item.w || 0.2) * els.canvas.width * state.zoom;
    const h = (item.h || 0.2) * els.canvas.height * state.zoom;
    ctx.drawImage(img, topLeft.x, topLeft.y, w, h);
    if (!isSelected) return;
    ctx.save();
    ctx.strokeStyle = "#2f6feb";
    ctx.lineWidth = 2;
    ctx.strokeRect(topLeft.x, topLeft.y, w, h);
    const hs = 8;
    ctx.fillStyle = "#2f6feb";
    ctx.fillRect(topLeft.x + w - hs / 2, topLeft.y + h - hs / 2, hs, hs);
    ctx.restore();
  }

  function updateImageActionsOverlay() {
    if (!isTeacher || state.tool !== "image" || !state.activeBoard || !state.selectedImageId) {
      els.imageActions.classList.add("hidden");
      return;
    }
    const item = (state.activeBoard.images || []).find((it) => it.id === state.selectedImageId);
    if (!item) {
      els.imageActions.classList.add("hidden");
      return;
    }
    const p = toScreen(item.x || 0, item.y || 0);
    const w = (item.w || 0.2) * els.canvas.width * state.zoom;
    const leftPx = (p.x + w + 8) / devicePixelRatio;
    const topPx = p.y / devicePixelRatio;
    els.imageActions.style.left = `${leftPx}px`;
    els.imageActions.style.top = `${topPx}px`;
    els.imageActions.classList.remove("hidden");
  }

  function imageHitTest(nx, ny) {
    const images = state.activeBoard ? state.activeBoard.images || [] : [];
    const handlePx = 14;
    const handleN = handlePx / Math.max(1, els.canvas.width * state.zoom);
    for (let i = images.length - 1; i >= 0; i--) {
      const it = images[i];
      const x = Number(it.x) || 0;
      const y = Number(it.y) || 0;
      const w = Number(it.w) || 0.2;
      const h = Number(it.h) || 0.2;
      if (nx < x || ny < y || nx > x + w || ny > y + h) continue;
      const nearResize = nx >= (x + w - handleN) && ny >= (y + h - handleN);
      return { item: it, mode: nearResize ? "resize" : "move" };
    }
    return null;
  }

  function clampImageBounds(item) {
    item.w = Math.max(0.03, Math.min(1, Number(item.w) || 0.2));
    item.h = Math.max(0.03, Math.min(1, Number(item.h) || 0.2));
    item.x = Math.max(0, Math.min(1 - item.w, Number(item.x) || 0));
    item.y = Math.max(0, Math.min(1 - item.h, Number(item.y) || 0));
  }

  function renderHotspots() {
    const layer = els.hotspotLayer;
    layer.innerHTML = "";
    if (!state.activeBoard || !Array.isArray(state.activeBoard.hotspots)) return;
    state.activeBoard.hotspots.forEach((h) => {
      const p = toScreen(Number(h.x || 0.5), Number(h.y || 0.5));
      const btn = document.createElement("button");
      btn.className = "hotspot " + (isTeacher ? "gear" : "viewer");
      btn.style.background = h.color || "#f39c12";
      btn.style.left = `${p.x / devicePixelRatio}px`;
      btn.style.top = `${p.y / devicePixelRatio}px`;
      btn.title = h.title || "Hotspot";
      btn.onpointerdown = (ev) => {
        ev.stopPropagation();
        if (!(isTeacher && state.tool === "hotspot") || ev.button !== 0) return;
        ev.preventDefault();
        const startX = ev.clientX;
        const startY = ev.clientY;
        let moved = false;

        const onMove = (mv) => {
          const dist = Math.hypot(mv.clientX - startX, mv.clientY - startY);
          if (dist > 3) moved = true;
          if (!moved) return;
          const np = fromEvent(mv);
          h.x = np.x;
          h.y = np.y;
          const sp = toScreen(h.x, h.y);
          btn.style.left = `${sp.x / devicePixelRatio}px`;
          btn.style.top = `${sp.y / devicePixelRatio}px`;
        };

        const onUp = () => {
          window.removeEventListener("pointermove", onMove);
          window.removeEventListener("pointerup", onUp);
          window.removeEventListener("pointercancel", onUp);
          if (moved) {
            send({ type: "hotspot_upsert", hotspot: h });
            render();
            return;
          }
          openHotspotEditor(h);
        };

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
        window.addEventListener("pointercancel", onUp);
      };
      btn.onclick = () => {
        if (isTeacher && state.tool === "hotspot") return;
        openHotspotContent(h);
      };
      layer.appendChild(btn);
    });
  }

  function render() {
    const ctx = els.canvas.getContext("2d");
    ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
    if (!state.activeBoard) {
      renderHotspots();
      return;
    }
    (state.activeBoard.images || []).forEach((it) => drawImageItem(ctx, it, it.id === state.selectedImageId));
    (state.activeBoard.strokes || []).forEach((s) => drawStroke(ctx, s));
    if (state.drawing && state.drawPoints.length > 1) {
      drawStroke(ctx, {
        tool: state.tool,
        color: state.color,
        size: state.size,
        points: state.drawPoints,
      });
    }
    renderHotspots();
    els.zoomLabel.textContent = `${Math.round(state.zoom * 100)}%`;
    const c = activeCourse();
    const wbName = state.activeBoard ? state.activeBoard.name : "";
    els.wbTitle.textContent = `${c ? c.name : "-"} / ${wbName}`;
    updateImageActionsOverlay();
  }

  function syncCatalog(catalog, activeBoard) {
    state.catalog = catalog;
    state.activeBoard = activeBoard;
    if (!state.selectedCourseId) state.selectedCourseId = catalog.activeCourseId;
    if (!state.selectedWbId) state.selectedWbId = catalog.activeWhiteboardId;
    const c = activeCourse();
    els.courseBtn.textContent = c ? `Cours: ${c.name}` : "Cours";
    renderCourseDialog();
    render();
    renderSupervisionChip();
    setStatus("Synchronisé");
  }

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const tenantQ = state.tenantKey ? `&t=${encodeURIComponent(state.tenantKey)}` : "";
    const ws = new WebSocket(`${proto}://${location.host}/ws/live?role=${isTeacher ? "teacher" : "student"}${tenantQ}`);
    state.ws = ws;
    ws.onopen = () => setStatus("Connecté");
    ws.onclose = () => {
      setStatus("Déconnecté - reconnexion...");
      setTimeout(connectWs, 900);
    };
    ws.onerror = () => setStatus("Erreur websocket");
    ws.onmessage = (ev) => {
      let msg = null;
      try {
        msg = JSON.parse(ev.data);
      } catch (_err) {
        return;
      }
      if (msg.type === "init") {
        state.users = Number(msg.users || 0);
        state.students = Number(msg.students || 0);
        if (msg.chatSupervision) state.supervision = msg.chatSupervision;
        if (msg.pdfIndexing) state.pdfs.indexing = msg.pdfIndexing;
        syncCatalog(msg.state, msg.activeBoard);
        renderSupervisionChip();
        return;
      }
      if (msg.type === "users") {
        state.users = Number(msg.count || 0);
        state.students = Number(msg.students || 0);
        state.supervision.queueLength = Number(msg.queue || 0);
        state.supervision.promptsSession = Number(msg.promptsSession || state.supervision.promptsSession || 0);
        renderSupervisionChip();
        setStatus("Connecté");
        return;
      }
      if (msg.type === "pdf_indexing") {
        if (!state.catalog || msg.courseId !== state.catalog.activeCourseId) return;
        const wasRunning = Boolean(state.pdfs.indexing && state.pdfs.indexing.running);
        state.pdfs.indexing = {
          running: Boolean(msg.running),
          error: String(msg.error || ""),
          updatedAt: Date.now(),
        };
        renderPdfDialog();
        if (wasRunning && !msg.running && !msg.error) {
          playBarkShort();
          if (state.pdfs.currentCourseId) {
            loadCoursePdfs(state.pdfs.currentCourseId).catch(() => {});
          }
        }
        return;
      }
      if (msg.type === "chat_supervision" && msg.data) {
        state.supervision = msg.data;
        renderSupervisionChip();
        if (els.supervisionDialog.open) renderSupervisionDialog();
        return;
      }
      if (msg.type === "llm_config" && msg.config) {
        state.llm = {
          provider: msg.config.provider === "apertus" ? "apertus" : "local",
          apertusModel: String(msg.config.apertusModel || ""),
        };
        renderLlmProviderButton();
        if (els.llmDialog.open) renderLlmConfigDialog();
        return;
      }
      if (msg.type === "catalog") {
        syncCatalog(msg.state, msg.activeBoard);
        return;
      }
      if (msg.sender && msg.sender === clientId) return;
      if (!state.activeBoard) return;

      if (msg.type === "stroke" && msg.stroke) {
        state.activeBoard.strokes.push(msg.stroke);
        render();
        return;
      }
      if (msg.type === "clear") {
        state.activeBoard.strokes = [];
        state.activeBoard.images = [];
        state.selectedImageId = null;
        render();
        return;
      }
      if (msg.type === "image_add" && msg.image) {
        state.activeBoard.images.push(msg.image);
        render();
        return;
      }
      if (msg.type === "image_update") {
        state.activeBoard.images = (state.activeBoard.images || []).map((it) =>
          it.id === msg.id ? { ...it, x: msg.x, y: msg.y, w: msg.w, h: msg.h } : it
        );
        render();
        return;
      }
      if (msg.type === "image_delete") {
        state.activeBoard.images = (state.activeBoard.images || []).filter((it) => it.id !== msg.id);
        if (state.selectedImageId === msg.id) state.selectedImageId = null;
        render();
        return;
      }
      if (msg.type === "hotspot_upsert" && msg.hotspot) {
        const hs = msg.hotspot;
        let found = false;
        state.activeBoard.hotspots = (state.activeBoard.hotspots || []).map((h) => {
          if (h.id === hs.id) {
            found = true;
            return hs;
          }
          return h;
        });
        if (!found) state.activeBoard.hotspots.push(hs);
        render();
        return;
      }
      if (msg.type === "hotspot_delete") {
        state.activeBoard.hotspots = (state.activeBoard.hotspots || []).filter((h) => h.id !== msg.id);
        render();
        return;
      }
      if (msg.type === "active_board_sync" && msg.board) {
        state.activeBoard = msg.board;
        if (!(state.activeBoard.images || []).some((it) => it.id === state.selectedImageId)) {
          state.selectedImageId = null;
        }
        render();
      }
    };
  }

  function send(msg) {
    const ws = state.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ ...msg, sender: clientId }));
    return true;
  }

  function activateWhiteboard(id) {
    send({ type: "activate_whiteboard", whiteboardId: id });
  }

  function openHotspotEditor(h) {
    if (!isTeacher) return;
    state.editingHotspot = { ...h };
    els.hotspotTitle.textContent = "Editer hotspot";
    els.hotspotName.value = h.title || "";
    els.hotspotColor.value = h.color || "#f39c12";
    els.hotspotHtml.value = h.html || "";
    els.hotspotDialog.showModal();
  }

  function openHotspotContent(h) {
    state.openHotspot = { ...h };
    els.contentTitle.textContent = h.title || "Hotspot";
    els.contentTitle.classList.add("hotspot-content-title");
    els.contentTitle.style.background = h.color || "#2f6feb";
    els.contentHtml.innerHTML = h.html || "<p>(vide)</p>";
    renderChatMessages();
    updateChatQueueStatus();
    els.contentDialog.showModal();
  }

  function openShare(kind) {
    const tk = state.tenantKey ? `&t=${encodeURIComponent(state.tenantKey)}` : "";
    const url =
      kind === "student"
        ? `${state.shareBaseUrl}/?mode=student${tk}`
        : `${state.shareBaseUrl}/?mode=teacher&remote=1${tk}`;
    els.shareTitle.textContent = kind === "student" ? "QR consultation etudiants" : "QR edition prof";
    els.shareUrl.value = url;
    els.shareQr.src = `/api/qr?url=${encodeURIComponent(url)}`;
    els.shareDialog.showModal();
  }

  function orderedHotspotsForPdf() {
    const hs = (state.activeBoard && state.activeBoard.hotspots) || [];
    return [...hs].sort((a, b) => String(a.title || "").localeCompare(String(b.title || ""), "fr"));
  }

  function renderExportCanvas() {
    const out = document.createElement("canvas");
    out.width = logical.w;
    out.height = logical.h;
    const ctx = out.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, out.width, out.height);
    (state.activeBoard.images || []).forEach((it) => {
      if (!it.src || !state.imageCache[it.src] || !state.imageCache[it.src].complete) return;
      ctx.drawImage(
        state.imageCache[it.src],
        (it.x || 0) * out.width,
        (it.y || 0) * out.height,
        (it.w || 0.2) * out.width,
        (it.h || 0.2) * out.height
      );
    });
    (state.activeBoard.strokes || []).forEach((s) => {
      if (!s.points || !s.points.length) return;
      if (s.tool === "watercolor") {
        const passes = [
          { mul: 2.8, alpha: 0.08 },
          { mul: 1.9, alpha: 0.12 },
          { mul: 1.2, alpha: 0.16 },
        ];
        ctx.save();
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = s.color || "#1a1a1a";
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        passes.forEach((p) => {
          ctx.globalAlpha = p.alpha;
          ctx.lineWidth = Math.max(1, Number(s.size || 2) * p.mul);
          ctx.beginPath();
          ctx.moveTo(s.points[0].x * out.width, s.points[0].y * out.height);
          for (let i = 1; i < s.points.length; i++) {
            ctx.lineTo(s.points[i].x * out.width, s.points[i].y * out.height);
          }
          ctx.stroke();
        });
        ctx.restore();
        return;
      }
      ctx.save();
      ctx.globalCompositeOperation = s.tool === "eraser" ? "destination-out" : "source-over";
      ctx.strokeStyle = s.color || "#1a1a1a";
      ctx.lineWidth = Number(s.size || 2);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(s.points[0].x * out.width, s.points[0].y * out.height);
      for (let i = 1; i < s.points.length; i++) {
        ctx.lineTo(s.points[i].x * out.width, s.points[i].y * out.height);
      }
      ctx.stroke();
      ctx.restore();
    });
    return out;
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportPng() {
    if (!state.activeBoard) return;
    const out = renderExportCanvas();
    out.toBlob((blob) => {
      if (!blob) return;
      const name = `${state.activeBoard.name || "whiteboard"}.png`;
      downloadBlob(blob, name);
    }, "image/png");
  }

  async function exportPdf() {
    if (!state.activeBoard || !state.catalog) return;
    const c = activeCourse();
    const out = renderExportCanvas();
    const imageDataUrl = out.toDataURL("image/png");
    const ordered = orderedHotspotsForPdf().map((h) => ({ title: h.title || "", html: h.html || "" }));
    const blob = await api("/api/export/pdf", {
      method: "POST",
      body: JSON.stringify({
        courseName: c ? c.name : "",
        whiteboardName: state.activeBoard.name || "",
        imageDataUrl,
        hotspots: ordered,
      }),
    });
    downloadBlob(blob, `${state.activeBoard.name || "whiteboard"}.pdf`);
  }

  async function loadCoursePdfs(courseId) {
    if (!courseId) return;
    const data = await api(`/api/courses/${courseId}/pdfs`);
    state.pdfs.currentCourseId = courseId;
    state.pdfs.files = data.files || [];
    state.pdfs.indexing = data.indexing || { running: false, error: "" };
    renderPdfDialog();
  }

  function renderPdfDialog() {
    const idx = state.pdfs.indexing || { running: false, error: "" };
    if (idx.running) {
      els.pdfStatus.textContent = "Indexation en cours...";
    } else if (idx.error) {
      els.pdfStatus.textContent = `Erreur indexation: ${idx.error}`;
    } else {
      els.pdfStatus.textContent = "Indexation prête.";
    }
    setPdfLoader(Boolean(idx.running));
    els.pdfList.innerHTML = "";
    (state.pdfs.files || []).forEach((f) => {
      const row = document.createElement("div");
      row.className = "pdf-row";
      const name = document.createElement("div");
      name.className = "pdf-name";
      name.textContent = `${f.name} (${Math.round((Number(f.size || 0) / 1024) * 10) / 10} KB)`;
      const renameBtn = document.createElement("button");
      renameBtn.className = "btn";
      renameBtn.textContent = "Renommer";
      renameBtn.onclick = async () => {
        const next = prompt("Nouveau nom PDF :", f.name);
        if (!next || next === f.name) return;
        await api(`/api/courses/${state.pdfs.currentCourseId}/pdfs/${encodeURIComponent(f.name)}`, {
          method: "PATCH",
          body: JSON.stringify({ newName: next }),
        });
        await loadCoursePdfs(state.pdfs.currentCourseId);
      };
      const delBtn = document.createElement("button");
      delBtn.className = "btn danger";
      delBtn.textContent = "Effacer";
      delBtn.onclick = async () => {
        if (!confirm(`Supprimer ${f.name} ?`)) return;
        await api(`/api/courses/${state.pdfs.currentCourseId}/pdfs/${encodeURIComponent(f.name)}`, { method: "DELETE" });
        await loadCoursePdfs(state.pdfs.currentCourseId);
      };
      row.append(name, renameBtn, delBtn);
      els.pdfList.appendChild(row);
    });
  }

  async function submitHotspotChatPrompt() {
    if (!state.openHotspot || !state.catalog || !state.activeBoard) return;
    const promptValue = (els.chatInput.value || "").trim();
    if (!promptValue || state.chat.pending) return;
    if (!ensureChatIdentity()) return;
    state.chat.pending = true;
    state.chat.messages.push({ role: "user", content: promptValue });
    els.chatInput.value = "";
    renderChatMessages();
    updateChatQueueStatus();
    const payload = {
      sessionId: state.chat.sessionId,
      studentName: state.chat.studentName,
      courseId: state.catalog.activeCourseId,
      whiteboardId: state.activeBoard.id,
      hotspotId: state.openHotspot.id || "",
      hotspotTitle: state.openHotspot.title || "",
      hotspotHtml: state.openHotspot.html || "",
      allHotspots: state.activeBoard.hotspots || [],
      prompt: promptValue,
    };
    const poll = async () => {
      try {
        const q = await api(`/api/chat/queue/${encodeURIComponent(state.chat.sessionId)}`);
        state.chat.queue = { active: !!q.active, position: Number(q.position || 0), queueLength: Number(q.queueLength || 0) };
        if (q.supervision) state.supervision = q.supervision;
        updateChatQueueStatus();
        renderSupervisionChip();
      } catch (_err) {}
    };
    poll();
    state.chat.pollTimer = window.setInterval(poll, 900);
    try {
      const startedAt = performance.now();
      const r = await api("/api/chat/hotspot", { method: "POST", body: JSON.stringify(payload) });
      const elapsedMs = performance.now() - startedAt;
      await animateAssistantText(r.answer || "(réponse vide)", "word", elapsedMs);
      state.chat.queue = r.session || { active: false, position: 0, queueLength: 0 };
      if (r.supervision) state.supervision = r.supervision;
      renderSupervisionChip();
      updateChatQueueStatus();
    } catch (e) {
      state.chat.messages.push({ role: "assistant", content: `Erreur: ${e.message || e}` });
      renderChatMessages();
    } finally {
      state.chat.pending = false;
      if (state.chat.pollTimer) {
        window.clearInterval(state.chat.pollTimer);
        state.chat.pollTimer = null;
      }
    }
  }

  async function exportWhiteboardFile() {
    if (!state.activeBoard) return;
    const blob = await api(`/api/whiteboards/${state.activeBoard.id}/export`);
    const safe = String(state.activeBoard.name || "whiteboard").replace(/[^A-Za-z0-9_.-]/g, "_");
    downloadBlob(blob, `${safe}.maxboard.json`);
  }

  async function importWhiteboardFromFile(file) {
    if (!file || !state.catalog) return;
    const text = await file.text();
    let payload = null;
    try {
      payload = JSON.parse(text);
    } catch (_err) {
      throw new Error("Fichier d'import invalide (JSON attendu).");
    }
    if (!payload || payload.format !== "maxboard.whiteboard.v1") {
      throw new Error("Format d'import non supporté.");
    }
    const activeCourseId = state.catalog.activeCourseId;
    await api("/api/whiteboards/import", {
      method: "POST",
      body: JSON.stringify({
        payload,
        targetCourseId: activeCourseId,
      }),
    });
  }

  function renderList(container, items, activeId, onClick, onDropReorder) {
    container.innerHTML = "";
    let dragId = null;
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "list-item" + (it.id === activeId ? " active" : "");
      row.textContent = it.name;
      row.draggable = isTeacher;
      row.onclick = () => onClick(it);
      row.ondragstart = () => {
        dragId = it.id;
      };
      row.ondragover = (ev) => ev.preventDefault();
      row.ondrop = (ev) => {
        ev.preventDefault();
        if (!dragId || dragId === it.id) return;
        const ids = items.map((x) => x.id);
        const a = ids.indexOf(dragId);
        const b = ids.indexOf(it.id);
        if (a < 0 || b < 0) return;
        ids.splice(b, 0, ids.splice(a, 1)[0]);
        onDropReorder(ids);
      };
      container.appendChild(row);
    });
  }

  function renderCourseDialog() {
    if (!state.catalog) return;
    const courseItems = state.catalog.courses.map((c) => ({ id: c.id, name: c.name }));
    renderList(
      els.courseList,
      courseItems,
      state.catalog.activeCourseId,
      (c) => {
        state.selectedCourseId = c.id;
        api(`/api/courses/${c.id}/activate`, { method: "POST" }).catch((e) => alert(e.message));
      },
      (ids) => api("/api/courses/reorder", { method: "POST", body: JSON.stringify({ courseIds: ids }) }).catch((e) => alert(e.message))
    );

    const c = state.catalog.courses.find((x) => x.id === (state.selectedCourseId || state.catalog.activeCourseId));
    const wbIds = c ? c.whiteboardOrder || [] : [];
    const wbItems = wbIds
      .map((id) => boardSummary(id))
      .filter(Boolean)
      .map((b) => ({ id: b.id, name: b.name }));
    renderList(
      els.wbList,
      wbItems,
      state.catalog.activeWhiteboardId,
      (wb) => {
        state.selectedWbId = wb.id;
        activateWhiteboard(wb.id);
      },
      (ids) =>
        c
          ? api(`/api/courses/${c.id}/whiteboards/reorder`, {
              method: "POST",
              body: JSON.stringify({ whiteboardIds: ids }),
            }).catch((e) => alert(e.message))
          : null
    );
  }

  function setTeacherVisibility() {
    if (isTeacher) {
      if (els.llmConfigBtn) els.llmConfigBtn.classList.remove("hidden");
      return;
    }
    els.courseBtn.classList.add("hidden");
    els.prevWbBtn.classList.add("hidden");
    els.nextWbBtn.classList.add("hidden");
    els.teacherTools.classList.add("hidden");
    els.shareTeacherBtn.classList.add("hidden");
    els.exportWbBtn.classList.add("hidden");
    els.importWbBtn.classList.add("hidden");
    if (els.llmConfigBtn) els.llmConfigBtn.classList.add("hidden");
    els.coursePdfsBtn.classList.add("hidden");
    els.supervisionChip.classList.add("hidden");
  }

  function setupEvents() {
    ensureLlmUi();
    document.querySelectorAll(".tool").forEach((b) => (b.onclick = () => chooseTool(b.dataset.tool)));
    els.colorInput.oninput = () => {
      state.color = String(els.colorInput.value || "#1a1a1a").toLowerCase();
      refreshPresetColorUI();
    };
    if (els.colorPresets) {
      els.colorPresets.querySelectorAll(".color-chip").forEach((chip) => {
        chip.style.background = chip.dataset.color || "#1a1a1a";
        chip.onclick = () => {
          const c = String(chip.dataset.color || "#1a1a1a").toLowerCase();
          state.color = c;
          els.colorInput.value = c;
          refreshPresetColorUI();
        };
      });
    }
    els.sizeInput.oninput = () => {
      state.size = Number(els.sizeInput.value || 3);
    };
    els.undoBtn.onclick = () => {
      if (!state.activeBoard) return;
      if ((state.activeBoard.strokes || []).length > 0) {
        state.activeBoard.strokes.pop();
        render();
      }
      send({ type: "undo_stroke" });
    };
    els.clearBtn.onclick = () => {
      if (!confirm("Effacer completement ce whiteboard ?")) return;
      if (state.activeBoard) {
        state.activeBoard.strokes = [];
        state.activeBoard.images = [];
        state.selectedImageId = null;
        render();
      }
      send({ type: "clear" });
    };
    els.imageDeleteBtn.onclick = () => {
      if (!state.activeBoard || !state.selectedImageId) return;
      const id = state.selectedImageId;
      state.activeBoard.images = (state.activeBoard.images || []).filter((it) => it.id !== id);
      state.selectedImageId = null;
      render();
      send({ type: "image_delete", id });
    };
    els.imageDuplicateBtn.onclick = () => {
      if (!state.activeBoard || !state.selectedImageId) return;
      const src = (state.activeBoard.images || []).find((it) => it.id === state.selectedImageId);
      if (!src) return;
      const dup = {
        ...src,
        id: makeId("img"),
        x: Math.min(0.94, (Number(src.x) || 0) + 0.03),
        y: Math.min(0.94, (Number(src.y) || 0) + 0.03),
      };
      clampImageBounds(dup);
      state.activeBoard.images.push(dup);
      state.selectedImageId = dup.id;
      render();
      send({ type: "image_add", image: dup });
    };
    els.zoomInBtn.onclick = () => {
      state.zoom = Math.min(3, state.zoom + 0.1);
      render();
    };
    els.zoomOutBtn.onclick = () => {
      state.zoom = Math.max(0.4, state.zoom - 0.1);
      render();
    };
    els.resetViewBtn.onclick = () => {
      state.zoom = 1;
      state.panX = 0;
      state.panY = 0;
      render();
      els.burgerMenu.classList.add("hidden");
    };
    els.burgerBtn.onclick = () => {
      els.burgerMenu.classList.toggle("hidden");
    };
    document.addEventListener("click", (e) => {
      const t = e.target;
      if (!els.burgerMenu.contains(t) && t !== els.burgerBtn) {
        els.burgerMenu.classList.add("hidden");
      }
    });
    els.shareStudentBtn.onclick = () => openShare("student");
    els.shareTeacherBtn.onclick = () => openShare("teacher");
    els.exportPngBtn.onclick = () => exportPng();
    els.exportPdfBtn.onclick = () => exportPdf().catch((e) => alert(e.message));
    els.exportWbBtn.onclick = () => {
      exportWhiteboardFile().catch((e) => alert(e.message));
      els.burgerMenu.classList.add("hidden");
    };
    els.importWbBtn.onclick = () => {
      els.importWbInput.value = "";
      els.importWbInput.click();
      els.burgerMenu.classList.add("hidden");
    };
    if (els.llmProviderSelect) {
      els.llmProviderSelect.onchange = () => updateLlmModelFieldState();
    }
    if (els.llmConfigBtn && els.llmDialog) {
      els.llmConfigBtn.onclick = () => {
        renderLlmConfigDialog();
        els.llmDialog.showModal();
        els.burgerMenu.classList.add("hidden");
      };
    }
    if (els.llmSaveBtn && els.llmProviderSelect && els.llmApertusModelInput && els.llmDialog) {
      els.llmSaveBtn.onclick = async () => {
        const payload = {
          provider: String(els.llmProviderSelect.value || "local"),
          apertusModel: String(els.llmApertusModelInput.value || "").trim(),
        };
        const res = await api("/api/llm/config", { method: "POST", body: JSON.stringify(payload) });
        if (res && res.config) {
          state.llm = {
            provider: res.config.provider === "apertus" ? "apertus" : "local",
            apertusModel: String(res.config.apertusModel || ""),
          };
        }
        renderLlmProviderButton();
        renderLlmConfigDialog();
        setStatus(`IA: ${state.llm.provider === "apertus" ? "Apertus" : "Qwen local"}`);
        els.llmDialog.close();
      };
    }
    if (els.llmCloseBtn && els.llmDialog) {
      els.llmCloseBtn.onclick = () => els.llmDialog.close();
    }
    els.pdfRefreshBtn.onclick = async () => {
      const c = activeCourse();
      if (!c) return;
      await loadCoursePdfs(c.id);
    };
    const openPdfDialog = async () => {
      const c = activeCourse();
      if (!c) return;
      await loadCoursePdfs(c.id);
      els.pdfDialog.showModal();
      els.burgerMenu.classList.add("hidden");
    };
    if (isTeacher) {
      const pdfEntry = document.createElement("button");
      pdfEntry.className = "menu-item";
      pdfEntry.textContent = "PDFs du cours";
      pdfEntry.onclick = () => {
        openPdfDialog().catch((e) => alert(e.message));
      };
      if (!els.burgerMenu.querySelector("[data-role='pdf-entry']")) {
        pdfEntry.dataset.role = "pdf-entry";
        els.burgerMenu.insertBefore(pdfEntry, els.resetViewBtn);
      }

      if (!els.burgerMenu.querySelector("[data-role='logout-entry']")) {
        const logoutEntry = document.createElement("button");
        logoutEntry.className = "menu-item";
        logoutEntry.dataset.role = "logout-entry";
        logoutEntry.textContent = "Se déconnecter";
        logoutEntry.onclick = async () => {
          await api("/api/auth/logout", { method: "POST" });
          location.reload();
        };
        els.burgerMenu.appendChild(logoutEntry);
      }

      if (!els.burgerMenu.querySelector("[data-role='password-entry']")) {
        const pwdEntry = document.createElement("button");
        pwdEntry.className = "menu-item";
        pwdEntry.dataset.role = "password-entry";
        pwdEntry.textContent = "Changer mon mot de passe";
        pwdEntry.onclick = () => {
          if (!els.passwordDialog) return;
          els.pwdCurrentInput.value = "";
          els.pwdNewInput.value = "";
          els.pwdConfirmInput.value = "";
          els.passwordDialog.showModal();
          els.burgerMenu.classList.add("hidden");
        };
        els.burgerMenu.appendChild(pwdEntry);
      }

      if (state.auth.user && state.auth.user.isAdmin && !els.burgerMenu.querySelector("[data-role='users-entry']")) {
        const usersEntry = document.createElement("button");
        usersEntry.className = "menu-item";
        usersEntry.dataset.role = "users-entry";
        usersEntry.textContent = "Gestion des profs";
        usersEntry.onclick = async () => {
          await loadUsersForAdmin();
          els.usersDialog.showModal();
          els.burgerMenu.classList.add("hidden");
        };
        els.burgerMenu.appendChild(usersEntry);
      }
    }

    if (els.pwdSaveBtn && els.passwordDialog) {
      els.pwdSaveBtn.onclick = async () => {
        try {
          const currentPassword = String(els.pwdCurrentInput.value || "");
          const newPassword = String(els.pwdNewInput.value || "");
          const confirmPassword = String(els.pwdConfirmInput.value || "");
          if (!currentPassword || !newPassword) {
            alert("Veuillez remplir les champs mot de passe.");
            return;
          }
          if (newPassword !== confirmPassword) {
            alert("La confirmation ne correspond pas.");
            return;
          }
          await api("/api/auth/change-password", {
            method: "POST",
            body: JSON.stringify({ currentPassword, newPassword }),
          });
          els.passwordDialog.close();
          setStatus("Mot de passe changé");
          alert("Mot de passe changé.");
        } catch (e) {
          alert(`Impossible de changer le mot de passe: ${e.message || e}`);
        }
      };
    }
    if (els.pwdCloseBtn && els.passwordDialog) {
      els.pwdCloseBtn.onclick = () => els.passwordDialog.close();
    }

    if (els.usersRefreshBtn) {
      els.usersRefreshBtn.onclick = () => {
        loadUsersForAdmin().catch((e) => alert(e.message));
      };
    }
    if (els.usersCreateBtn) {
      els.usersCreateBtn.onclick = async () => {
        const username = String(els.newUserNameInput.value || "").trim();
        const password = String(els.newUserPasswordInput.value || "");
        const isAdminUser = Boolean(els.newUserAdminInput.checked);
        if (!username || !password) {
          alert("Nom d'utilisateur et mot de passe requis.");
          return;
        }
        await api("/api/auth/users", {
          method: "POST",
          body: JSON.stringify({ username, password, isAdmin: isAdminUser }),
        });
        els.newUserNameInput.value = "";
        els.newUserPasswordInput.value = "";
        els.newUserAdminInput.checked = false;
        await loadUsersForAdmin();
      };
    }
    if (els.usersCloseBtn && els.usersDialog) {
      els.usersCloseBtn.onclick = () => els.usersDialog.close();
    }
    els.importWbInput.onchange = async () => {
      const file = els.importWbInput.files && els.importWbInput.files[0];
      if (!file) return;
      try {
        await importWhiteboardFromFile(file);
        setStatus("Whiteboard importé");
      } catch (e) {
        alert(e && e.message ? e.message : "Import impossible.");
      }
    };
    els.shareCopyBtn.onclick = async () => {
      await navigator.clipboard.writeText(els.shareUrl.value);
      setStatus("URL copiée");
    };
    els.shareCloseBtn.onclick = () => els.shareDialog.close();
    els.courseBtn.onclick = () => {
      renderCourseDialog();
      els.courseDialog.showModal();
    };

    els.prevWbBtn.onclick = () => {
      const order = wbOrder();
      if (!order.length) return;
      const i = order.indexOf(state.catalog.activeWhiteboardId);
      const prev = i <= 0 ? order[order.length - 1] : order[i - 1];
      activateWhiteboard(prev);
    };
    els.nextWbBtn.onclick = () => {
      const order = wbOrder();
      if (!order.length) return;
      const i = order.indexOf(state.catalog.activeWhiteboardId);
      const next = i < 0 || i >= order.length - 1 ? order[0] : order[i + 1];
      activateWhiteboard(next);
    };

    els.courseCreateBtn.onclick = async () => {
      const name = prompt("Nom du cours ?", "Nouveau cours");
      if (!name) return;
      await api("/api/courses", { method: "POST", body: JSON.stringify({ name }) });
    };
    els.courseRenameBtn.onclick = async () => {
      const id = state.catalog.activeCourseId;
      const c = activeCourse();
      if (!c) return;
      const name = prompt("Nouveau nom du cours ?", c.name);
      if (!name) return;
      await api(`/api/courses/${id}`, { method: "PATCH", body: JSON.stringify({ name }) });
    };
    els.courseDuplicateBtn.onclick = async () => {
      const id = state.catalog.activeCourseId;
      await api(`/api/courses/${id}/duplicate`, { method: "POST" });
    };
    els.coursePdfsBtn.onclick = async () => {
      const c = activeCourse();
      if (!c) return;
      await loadCoursePdfs(c.id);
      els.pdfDialog.showModal();
    };
    els.courseDeleteBtn.onclick = async () => {
      const id = state.catalog.activeCourseId;
      if (!confirm("Suppression definitive du cours et de ses whiteboards ?")) return;
      await api(`/api/courses/${id}`, { method: "DELETE" });
    };

    els.wbCreateBtn.onclick = async () => {
      const c = activeCourse();
      if (!c) return;
      const name = prompt("Nom du whiteboard ?", "Nouveau whiteboard");
      if (!name) return;
      await api(`/api/courses/${c.id}/whiteboards`, { method: "POST", body: JSON.stringify({ name }) });
    };
    els.wbRenameBtn.onclick = async () => {
      const wb = state.activeBoard;
      if (!wb) return;
      const name = prompt("Nouveau nom du whiteboard ?", wb.name);
      if (!name) return;
      await api(`/api/whiteboards/${wb.id}`, { method: "PATCH", body: JSON.stringify({ name }) });
    };
    els.wbDuplicateBtn.onclick = async () => {
      const wb = state.activeBoard;
      if (!wb) return;
      await api(`/api/whiteboards/${wb.id}/duplicate`, { method: "POST", body: JSON.stringify({}) });
    };
    els.wbCopyToCourseBtn.onclick = async () => {
      const wb = state.activeBoard;
      if (!wb) return;
      const targetCourseId = chooseTargetCourseId(wb.courseId);
      if (!targetCourseId) return;
      const target = courseById(targetCourseId);
      const ok = confirm(`Copier "${wb.name}" vers "${target ? target.name : "ce cours"}" ?`);
      if (!ok) return;
      await api(`/api/whiteboards/${wb.id}/duplicate`, {
        method: "POST",
        body: JSON.stringify({ targetCourseId }),
      });
      setStatus("Whiteboard copié");
    };
    els.wbDeleteBtn.onclick = async () => {
      const wb = state.activeBoard;
      if (!wb) return;
      if (!confirm("Suppression definitive du whiteboard ?")) return;
      await api(`/api/whiteboards/${wb.id}`, { method: "DELETE" });
    };

    els.hotspotCancelBtn.onclick = () => els.hotspotDialog.close();
    els.hotspotSaveBtn.onclick = () => {
      if (!state.editingHotspot) return;
      const hs = {
        ...state.editingHotspot,
        title: els.hotspotName.value.trim() || "Hotspot",
        color: els.hotspotColor.value,
        html: els.hotspotHtml.value,
      };
      let found = false;
      state.activeBoard.hotspots = (state.activeBoard.hotspots || []).map((item) => {
        if (item.id === hs.id) {
          found = true;
          return hs;
        }
        return item;
      });
      if (!found) state.activeBoard.hotspots.push(hs);
      render();
      send({ type: "hotspot_upsert", hotspot: hs });
      els.hotspotDialog.close();
    };
    els.hotspotDeleteBtn.onclick = () => {
      if (!state.editingHotspot) return;
      if (!confirm("Supprimer ce hotspot ?")) return;
      state.activeBoard.hotspots = (state.activeBoard.hotspots || []).filter((h) => h.id !== state.editingHotspot.id);
      render();
      send({ type: "hotspot_delete", id: state.editingHotspot.id });
      els.hotspotDialog.close();
    };
    els.chatSendBtn.onclick = () => {
      submitHotspotChatPrompt().catch((e) => {
        alert(e.message || e);
      });
    };
    els.chatInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        submitHotspotChatPrompt().catch((e) => {
          alert(e.message || e);
        });
      }
    });
    els.chatReleaseBtn.onclick = async () => {
      if (!state.chat.sessionId) return;
      await api("/api/chat/release", {
        method: "POST",
        body: JSON.stringify({ sessionId: state.chat.sessionId }),
      });
      state.chat.messages = [];
      state.chat.queue = { active: false, position: 0, queueLength: 0 };
      renderChatMessages();
      updateChatQueueStatus();
    };
    els.supervisionChip.onclick = () => {
      if (!isTeacher) return;
      renderSupervisionDialog();
      els.supervisionDialog.showModal();
    };
    els.importWbInput.addEventListener("click", (ev) => ev.stopPropagation());
    els.pdfUploadBtn.onclick = () => {
      const c = activeCourse();
      if (!c) return;
      els.pdfUploadInput.value = "";
      els.pdfUploadInput.click();
    };
    els.pdfUploadInput.onchange = async () => {
      const c = activeCourse();
      const f = els.pdfUploadInput.files && els.pdfUploadInput.files[0];
      if (!c || !f) return;
      const form = new FormData();
      form.append("file", f);
      const tk = state.tenantKey ? `?t=${encodeURIComponent(state.tenantKey)}` : "";
      const r = await fetch(`/api/courses/${c.id}/pdfs/upload${tk}`, { method: "POST", body: form, credentials: "same-origin" });
      if (!r.ok) {
        const txt = await r.text();
        alert(txt || `Upload impossible (${r.status})`);
        return;
      }
      await loadCoursePdfs(c.id);
    };
    els.pdfCloseBtn.onclick = () => els.pdfDialog.close();
    els.contentDialog.addEventListener("close", () => {
      state.openHotspot = null;
      if (state.chat.pollTimer) {
        window.clearInterval(state.chat.pollTimer);
        state.chat.pollTimer = null;
      }
    });

    let pointerId = null;
    els.stage.addEventListener("pointerdown", (ev) => {
      if (state.pinch) return;
      if (ev.pointerType === "touch" && ev.isPrimary === false) return;
      if (isTeacher && state.tool === "hotspot" && ev.button === 0) {
        const p = fromEvent(ev);
        const hs = {
          id: "hs_" + Date.now(),
          x: p.x,
          y: p.y,
          title: "Hotspot",
          html: "<p>Contenu du hotspot</p>",
          color: "#f39c12",
        };
        openHotspotEditor(hs);
        return;
      }
      if (isTeacher && state.activeBoard && state.tool === "image" && ev.button === 0) {
        const p = fromEvent(ev);
        const hit = imageHitTest(p.x, p.y);
        if (hit) {
          state.selectedImageId = hit.item.id;
          state.imageDrag = {
            pointerId: ev.pointerId,
            id: hit.item.id,
            mode: hit.mode,
            startX: p.x,
            startY: p.y,
            x: Number(hit.item.x) || 0,
            y: Number(hit.item.y) || 0,
            w: Number(hit.item.w) || 0.2,
            h: Number(hit.item.h) || 0.2,
          };
          render();
          return;
        }
        if (state.selectedImageId) {
          state.selectedImageId = null;
          render();
          return;
        }
      }
      if (!isTeacher || ev.altKey || ev.button === 1 || ev.button === 2) {
        state.panning = true;
        state.panStart = { x: ev.clientX, y: ev.clientY, panX: state.panX, panY: state.panY };
        return;
      }
      if (state.tool !== "pen" && state.tool !== "eraser" && state.tool !== "watercolor") return;
      pointerId = ev.pointerId;
      state.drawing = true;
      state.drawPoints = [fromEvent(ev)];
      render();
    });

    els.stage.addEventListener("pointermove", (ev) => {
      if (state.imageDrag && ev.pointerId === state.imageDrag.pointerId && state.activeBoard) {
        const drag = state.imageDrag;
        const p = fromEvent(ev);
        const img = (state.activeBoard.images || []).find((it) => it.id === drag.id);
        if (!img) return;
        if (drag.mode === "move") {
          img.x = drag.x + (p.x - drag.startX);
          img.y = drag.y + (p.y - drag.startY);
        } else {
          img.w = drag.w + (p.x - drag.startX);
          img.h = drag.h + (p.y - drag.startY);
        }
        clampImageBounds(img);
        render();
        send({ type: "image_update", id: img.id, x: img.x, y: img.y, w: img.w, h: img.h });
        return;
      }
      if (state.panning && state.panStart) {
        state.panX = state.panStart.panX + (ev.clientX - state.panStart.x) * devicePixelRatio;
        state.panY = state.panStart.panY + (ev.clientY - state.panStart.y) * devicePixelRatio;
        render();
        return;
      }
      if (!state.drawing || ev.pointerId !== pointerId) return;
      state.drawPoints.push(fromEvent(ev));
      render();
    });

    const finishDraw = () => {
      if (state.imageDrag) {
        state.imageDrag = null;
        return;
      }
      if (state.panning) {
        state.panning = false;
        state.panStart = null;
        return;
      }
      if (!state.drawing) return;
      state.drawing = false;
      if (state.drawPoints.length > 1) {
        const stroke = {
          id: "s_" + Date.now(),
          tool: state.tool,
          color: state.color,
          size: state.size,
          points: state.drawPoints,
        };
        state.activeBoard.strokes.push(stroke);
        send({ type: "stroke", stroke });
      }
      state.drawPoints = [];
      render();
    };
    els.stage.addEventListener("pointerup", finishDraw);
    els.stage.addEventListener("pointercancel", finishDraw);
    els.stage.addEventListener("pointerleave", finishDraw);

    els.stage.addEventListener(
      "wheel",
      (ev) => {
        ev.preventDefault();
        const before = state.zoom;
        state.zoom = Math.max(0.4, Math.min(3, state.zoom + (ev.deltaY < 0 ? 0.08 : -0.08)));
        if (before !== state.zoom) render();
      },
      { passive: false }
    );

    els.stage.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
    });

    els.stage.addEventListener(
      "touchstart",
      (ev) => {
        if (ev.touches.length === 2) {
          const a = ev.touches[0];
          const b = ev.touches[1];
          const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
          state.pinch = { dist, zoom: state.zoom };
        }
      },
      { passive: true }
    );
    els.stage.addEventListener(
      "touchmove",
      (ev) => {
        if (ev.touches.length !== 2 || !state.pinch) return;
        ev.preventDefault();
        const a = ev.touches[0];
        const b = ev.touches[1];
        const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
        const ratio = dist / Math.max(1, state.pinch.dist);
        state.zoom = Math.max(0.4, Math.min(3, state.pinch.zoom * ratio));
        render();
      },
      { passive: false }
    );
    els.stage.addEventListener("touchend", () => {
      if (state.pinch) state.pinch = null;
    });

    window.addEventListener("resize", resizeCanvas);

    window.addEventListener("paste", (ev) => {
      if (!isTeacher || !state.activeBoard) return;
      const tag = (document.activeElement && document.activeElement.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      const items = ev.clipboardData && ev.clipboardData.items ? ev.clipboardData.items : [];
      for (const item of items) {
        if (!item.type || !item.type.startsWith("image/")) continue;
        const file = item.getAsFile();
        if (!file) continue;
        const reader = new FileReader();
        reader.onload = () => {
          const src = String(reader.result || "");
          const image = {
            id: makeId("img"),
            src,
            x: 0.35,
            y: 0.3,
            w: 0.3,
            h: 0.3,
          };
          state.activeBoard.images.push(image);
          state.selectedImageId = image.id;
          send({ type: "image_add", image });
          render();
        };
        reader.readAsDataURL(file);
        ev.preventDefault();
        break;
      }
    });
  }

  async function init() {
    ensureLlmUi();
    await ensureTeacherAuth();
    setTeacherVisibility();
    setupEvents();
    const data = await api("/api/bootstrap");
    state.shareBaseUrl = data.shareBaseUrl || location.origin;
    if (data.tenantKey) state.tenantKey = String(data.tenantKey || "");
    if (data.chatSupervision) state.supervision = data.chatSupervision;
    if (data.pdfIndexing) state.pdfs.indexing = data.pdfIndexing;
    if (data.auth) {
      state.auth.authenticated = Boolean(data.auth.authenticated);
      state.auth.user = data.auth.user || null;
    }
    if (data.llmConfig) {
      state.llm = {
        provider: data.llmConfig.provider === "apertus" ? "apertus" : "local",
        apertusModel: String(data.llmConfig.apertusModel || ""),
      };
    } else if (data.llmProvider) {
      state.llm.provider = data.llmProvider === "apertus" ? "apertus" : "local";
    }
    renderLlmProviderButton();
    syncCatalog(data.state, data.activeBoard);
    state.color = String(els.colorInput.value || "#1a1a1a").toLowerCase();
    state.size = Number(els.sizeInput.value || 3);
    refreshPresetColorUI();
    renderSupervisionDialog();
    renderSupervisionChip();
    renderLlmConfigDialog();
    updateChatQueueStatus();
    resizeCanvas();
    connectWs();
    setStatus("Prêt");
  }

  init().catch((e) => {
    console.error(e);
    alert(String(e.message || e));
  });
})();
