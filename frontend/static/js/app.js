(function () {
  "use strict";

  const state = {
    conversationId: null,
    projectId: "",
    mode: "general",
    pendingOcrText: null,
  };

  const el = {
    modeSelect: document.getElementById("mode-select"),
    projectSelect: document.getElementById("project-select"),
    marksGroup: document.getElementById("marks-group"),
    marksSelect: document.getElementById("marks-select"),
    ragToggle: document.getElementById("rag-toggle"),
    messages: document.getElementById("messages"),
    composer: document.getElementById("composer"),
    messageInput: document.getElementById("message-input"),
    conversationList: document.getElementById("conversation-list"),
    newChatBtn: document.getElementById("new-chat-btn"),
    newProjectBtn: document.getElementById("new-project-btn"),
    imageInput: document.getElementById("image-input"),
    docInput: document.getElementById("doc-input"),
    attachImageBtn: document.getElementById("attach-image-btn"),
    attachDocBtn: document.getElementById("attach-doc-btn"),
    ocrPreview: document.getElementById("ocr-preview"),
    ocrText: document.getElementById("ocr-text"),
    ocrDismiss: document.getElementById("ocr-dismiss"),
    documentsLink: document.getElementById("documents-link"),
    diagnosticsLink: document.getElementById("diagnostics-link"),
    clearMemoryLink: document.getElementById("clear-memory-link"),
    chatView: document.getElementById("chat-view"),
    documentsView: document.getElementById("documents-view"),
    diagnosticsView: document.getElementById("diagnostics-view"),
    documentsList: document.getElementById("documents-list"),
    diagnosticsOutput: document.getElementById("diagnostics-output"),
    backFromDocuments: document.getElementById("back-from-documents"),
    backFromDiagnostics: document.getElementById("back-from-diagnostics"),
  };

  function showView(view) {
    el.chatView.hidden = view !== "chat";
    el.documentsView.hidden = view !== "documents";
    el.diagnosticsView.hidden = view !== "diagnostics";
  }

  function addMessage(role, content, ragSources) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = window.LLA_renderMarkdown(content || "");
    wrapper.appendChild(bubble);

    if (ragSources && ragSources.length) {
      const src = document.createElement("div");
      src.className = "rag-sources";
      src.textContent = "Sources: " + ragSources.map((s) => `${s.source} (${s.score})`).join(", ");
      wrapper.appendChild(src);
    }

    el.messages.appendChild(wrapper);
    el.messages.scrollTop = el.messages.scrollHeight;
    return bubble;
  }

  async function loadModes() {
    const modes = await LLA_API.getModes();
    el.modeSelect.innerHTML = modes.map((m) => `<option value="${m.id}">${m.label}</option>`).join("");
    el.modeSelect.value = state.mode;
  }

  async function loadProjects() {
    const projects = await LLA_API.listProjects();
    const options = ['<option value="">(none)</option>']
      .concat(projects.map((p) => `<option value="${p.id}">${p.name}</option>`));
    el.projectSelect.innerHTML = options.join("");
  }

  async function loadConversations() {
    const conversations = await LLA_API.listConversations(state.projectId || undefined);
    el.conversationList.innerHTML = "";
    for (const c of conversations) {
      const li = document.createElement("li");
      li.textContent = c.title || "(untitled)";
      li.dataset.id = c.id;
      if (c.id === state.conversationId) li.classList.add("active");
      li.addEventListener("click", () => openConversation(c.id));
      el.conversationList.appendChild(li);
    }
  }

  async function openConversation(conversationId) {
    state.conversationId = conversationId;
    el.messages.innerHTML = "";
    const messages = await LLA_API.getMessages(conversationId);
    for (const m of messages) {
      addMessage(m.role, m.content);
    }
    await loadConversations();
  }

  function newChat() {
    state.conversationId = null;
    el.messages.innerHTML = "";
    loadConversations();
  }

  el.modeSelect.addEventListener("change", () => {
    state.mode = el.modeSelect.value;
    el.marksGroup.style.display = state.mode === "exam" ? "flex" : "none";
  });

  el.projectSelect.addEventListener("change", () => {
    state.projectId = el.projectSelect.value;
    newChat();
  });

  el.newChatBtn.addEventListener("click", newChat);

  el.newProjectBtn.addEventListener("click", async () => {
    const name = prompt("Project name:");
    if (!name) return;
    await LLA_API.createProject(name);
    await loadProjects();
  });

  el.attachImageBtn.addEventListener("click", () => el.imageInput.click());
  el.attachDocBtn.addEventListener("click", () => el.docInput.click());

  el.imageInput.addEventListener("change", async () => {
    const file = el.imageInput.files[0];
    if (!file) return;
    el.attachImageBtn.textContent = "...";
    try {
      const result = await LLA_API.uploadImageForOcr(file);
      state.pendingOcrText = result.text;
      el.ocrText.value = result.text;
      el.ocrPreview.hidden = false;
    } catch (e) {
      alert("OCR failed: " + e.message);
    } finally {
      el.attachImageBtn.textContent = "[img]";
      el.imageInput.value = "";
    }
  });

  el.ocrDismiss.addEventListener("click", () => {
    state.pendingOcrText = null;
    el.ocrPreview.hidden = true;
  });

  el.docInput.addEventListener("change", async () => {
    const file = el.docInput.files[0];
    if (!file) return;
    el.attachDocBtn.textContent = "...";
    try {
      const result = await LLA_API.uploadDocument(file, state.projectId || undefined);
      addMessage("assistant", `Indexed **${result.filename}** into local RAG (${result.chunk_count} chunks). Enable "Use my documents" to retrieve from it.`);
      el.ragToggle.checked = true;
    } catch (e) {
      alert("Upload failed: " + e.message);
    } finally {
      el.attachDocBtn.textContent = "[doc]";
      el.docInput.value = "";
    }
  });

  el.composer.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const text = el.messageInput.value.trim();
    if (!text) return;

    addMessage("user", text);
    el.messageInput.value = "";

    const ocrText = state.pendingOcrText;
    state.pendingOcrText = null;
    el.ocrPreview.hidden = true;

    const assistantBubble = addMessage("assistant", "...");
    let accumulated = "";

    const payload = {
      message: text,
      mode: state.mode,
      conversation_id: state.conversationId,
      project_id: state.projectId || null,
      marks: el.marksSelect.value ? parseInt(el.marksSelect.value, 10) : null,
      use_rag: el.ragToggle.checked,
      ocr_text: ocrText,
    };

    try {
      await LLA_API.streamChat(payload, (event) => {
        if (event.type === "meta") {
          state.conversationId = event.conversation_id;
          if (event.rag_sources && event.rag_sources.length) {
            const src = document.createElement("div");
            src.className = "rag-sources";
            src.textContent = "Sources: " + event.rag_sources.map((s) => `${s.source} (${s.score})`).join(", ");
            assistantBubble.parentElement.appendChild(src);
          }
        } else if (event.type === "delta") {
          accumulated += event.content;
          assistantBubble.innerHTML = window.LLA_renderMarkdown(accumulated);
          el.messages.scrollTop = el.messages.scrollHeight;
        } else if (event.type === "error") {
          assistantBubble.innerHTML = window.LLA_renderMarkdown(`**Error:** ${event.message}`);
        }
      });
    } catch (e) {
      assistantBubble.innerHTML = window.LLA_renderMarkdown(`**Error:** ${e.message}`);
    }

    await loadConversations();
  });

  el.messageInput.addEventListener("keydown", (evt) => {
    if (evt.key === "Enter" && !evt.shiftKey) {
      evt.preventDefault();
      el.composer.requestSubmit();
    }
  });

  el.documentsLink.addEventListener("click", async (evt) => {
    evt.preventDefault();
    const docs = await LLA_API.listDocuments(state.projectId || undefined);
    el.documentsList.innerHTML = docs
      .map((d) => `<li><span>${d.filename}</span><button class="btn btn-small" data-id="${d.id}">Delete</button></li>`)
      .join("");
    el.documentsList.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await LLA_API.deleteDocument(btn.dataset.id);
        btn.closest("li").remove();
      });
    });
    showView("documents");
  });

  el.diagnosticsLink.addEventListener("click", async (evt) => {
    evt.preventDefault();
    const diag = await LLA_API.getDiagnostics();
    el.diagnosticsOutput.textContent = JSON.stringify(diag, null, 2);
    showView("diagnostics");
  });

  el.clearMemoryLink.addEventListener("click", async (evt) => {
    evt.preventDefault();
    if (!confirm("This will permanently delete all local conversations, projects, and notes. Continue?")) return;
    await LLA_API.clearMemory();
    newChat();
    await loadProjects();
  });

  el.backFromDocuments.addEventListener("click", () => showView("chat"));
  el.backFromDiagnostics.addEventListener("click", () => showView("chat"));

  (async function init() {
    await Promise.all([loadModes(), loadProjects(), loadConversations()]);
  })();
})();
