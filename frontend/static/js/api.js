// Thin fetch wrappers for the LOCAL-LAB-AI backend API. All requests go to
// the same origin the UI was served from (the local loopback backend) -
// there is no CDN or external endpoint anywhere in this file.

const LLA_API = {
  async getModes() {
    return (await fetch("/api/modes")).json();
  },

  async listConversations(projectId) {
    const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    return (await fetch(`/api/conversations${qs}`)).json();
  },

  async getMessages(conversationId) {
    return (await fetch(`/api/conversations/${conversationId}/messages`)).json();
  },

  async deleteConversation(conversationId) {
    return (await fetch(`/api/conversations/${conversationId}`, { method: "DELETE" })).json();
  },

  async listProjects() {
    return (await fetch("/api/projects")).json();
  },

  async createProject(name) {
    const resp = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    return resp.json();
  },

  async listDocuments(projectId) {
    const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    return (await fetch(`/api/documents${qs}`)).json();
  },

  async uploadDocument(file, projectId) {
    const form = new FormData();
    form.append("file", file);
    const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    const resp = await fetch(`/api/documents${qs}`, { method: "POST", body: form });
    return resp.json();
  },

  async deleteDocument(documentId) {
    return (await fetch(`/api/documents/${documentId}`, { method: "DELETE" })).json();
  },

  async uploadImageForOcr(file) {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/ocr", { method: "POST", body: form });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "OCR failed");
    }
    return resp.json();
  },

  async getDiagnostics() {
    return (await fetch("/api/diagnostics")).json();
  },

  async clearMemory() {
    return (await fetch("/api/memory/clear", { method: "POST" })).json();
  },

  // Streams chat completions via Server-Sent Events. `onEvent` receives
  // parsed JSON objects of shape {type: 'meta'|'delta'|'error'|'done', ...}.
  async streamChat(payload, onEvent) {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok || !resp.body) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Chat request failed");
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice("data:".length).trim();
        try {
          onEvent(JSON.parse(jsonStr));
        } catch (e) {
          console.warn("Failed to parse SSE chunk", jsonStr);
        }
      }
    }
  },
};
