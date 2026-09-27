// Minimal, dependency-free markdown renderer + code highlighter.
// No CDN, no external libraries: kept intentionally small so the whole
// frontend works with zero network access.

(function (global) {
  "use strict";

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const KEYWORDS = new Set([
    "if", "else", "for", "while", "do", "switch", "case", "break", "continue",
    "return", "function", "def", "class", "public", "private", "protected",
    "static", "void", "int", "float", "double", "char", "long", "short",
    "const", "let", "var", "import", "from", "include", "using", "namespace",
    "try", "catch", "finally", "throw", "new", "delete", "struct", "enum",
    "select", "from", "where", "insert", "update", "delete", "create", "table",
    "begin", "end", "procedure", "trigger", "cursor", "exception", "null",
    "true", "false", "None", "self", "this", "async", "await",
  ]);

  function highlightCode(code) {
    const escaped = escapeHtml(code);
    const lines = escaped.split("\n");
    return lines
      .map((line) => {
        let out = "";
        let i = 0;
        while (i < line.length) {
          const rest = line.slice(i);

          const commentMatch = rest.match(/^(\/\/.*|#.*|--.*)/);
          if (commentMatch) {
            out += `<span class="tok-com">${commentMatch[0]}</span>`;
            break;
          }

          const strMatch = rest.match(/^("([^"\\]|\\.)*"|'([^'\\]|\\.)*')/);
          if (strMatch) {
            out += `<span class="tok-str">${strMatch[0]}</span>`;
            i += strMatch[0].length;
            continue;
          }

          const numMatch = rest.match(/^\b\d+(\.\d+)?\b/);
          if (numMatch) {
            out += `<span class="tok-num">${numMatch[0]}</span>`;
            i += numMatch[0].length;
            continue;
          }

          const wordMatch = rest.match(/^[A-Za-z_]\w*/);
          if (wordMatch) {
            const word = wordMatch[0];
            if (KEYWORDS.has(word.toLowerCase())) {
              out += `<span class="tok-kw">${word}</span>`;
            } else {
              out += word;
            }
            i += word.length;
            continue;
          }

          out += line[i];
          i += 1;
        }
        return out;
      })
      .join("\n");
  }

  function renderInline(text) {
    let out = escapeHtml(text);
    out = out.replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`);
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return out;
  }

  function render(markdown) {
    const lines = markdown.replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let i = 0;
    let inList = false;

    while (i < lines.length) {
      const line = lines[i];

      const fenceMatch = line.match(/^```(\w*)\s*$/);
      if (fenceMatch) {
        const lang = fenceMatch[1] || "text";
        const codeLines = [];
        i += 1;
        while (i < lines.length && !/^```\s*$/.test(lines[i])) {
          codeLines.push(lines[i]);
          i += 1;
        }
        i += 1; // skip closing fence
        const rawCode = codeLines.join("\n");
        html += `<pre data-raw="${escapeHtml(rawCode).replace(/"/g, "&quot;")}"><button class="copy-btn" onclick="LLA_copyCode(this)">Copy</button><code class="lang-${lang}">${highlightCode(rawCode)}</code></pre>\n`;
        continue;
      }

      if (/^#{1,6}\s/.test(line)) {
        const level = line.match(/^#+/)[0].length;
        html += `<h${level}>${renderInline(line.replace(/^#{1,6}\s/, ""))}</h${level}>\n`;
        i += 1;
        continue;
      }

      if (/^\s*[-*]\s+/.test(line)) {
        if (!inList) {
          html += "<ul>\n";
          inList = true;
        }
        html += `<li>${renderInline(line.replace(/^\s*[-*]\s+/, ""))}</li>\n`;
        i += 1;
        continue;
      } else if (inList) {
        html += "</ul>\n";
        inList = false;
      }

      if (line.trim() === "") {
        html += "\n";
        i += 1;
        continue;
      }

      html += `<p>${renderInline(line)}</p>\n`;
      i += 1;
    }

    if (inList) html += "</ul>\n";
    return html;
  }

  global.LLA_renderMarkdown = render;

  global.LLA_copyCode = function (btn) {
    const pre = btn.closest("pre");
    const raw = pre.getAttribute("data-raw");
    navigator.clipboard.writeText(raw).then(() => {
      const original = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = original), 1200);
    });
  };
})(window);
