"use client";

import React, { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [status, setStatus] = useState(null);
  const [modelUsed, setModelUsed] = useState(null);

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);
    setStatus(null);
    setModelUsed(null);

    try {
      const res = await fetch("http://localhost:8000/research", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      setResponse(data.response);
      setStatus(data.status);
      setModelUsed(data.model_used);
    } catch (err) {
      setResponse(
        `Failed to connect to the backend server.\n\n` +
        `Please verify that the FastAPI backend server is running on \`http://localhost:8000\`:\n` +
        `\`python main.py\` or \`uvicorn main:app --reload\`\n\n` +
        `Technical Details:\n${err.message || err}`
      );
      setStatus("CONNECTION_ERROR");
      setModelUsed("None");
    } finally {
      setLoading(false);
    }
  };

  // Modern, robust Vanilla JS markdown parser for instant styled HTML rendering
  const parseMarkdown = (text) => {
    if (!text) return "";

    // Process markdown line-by-line for highly precise structure
    const lines = text.split("\n");
    let inList = false;
    let inCodeBlock = false;
    let codeContent = [];
    const htmlLines = [];

    for (let line of lines) {
      // Handle code block boundary
      if (line.trim().startsWith("```")) {
        if (inCodeBlock) {
          // Close code block
          htmlLines.push(`<pre><code>${codeContent.join("\n")}</code></pre>`);
          codeContent = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        continue;
      }

      // Collect code block lines
      if (inCodeBlock) {
        // Escape HTML tags inside code blocks
        const escapedCodeLine = line
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
        codeContent.push(escapedCodeLine);
        continue;
      }

      // Handle list boundary
      const listMatch = line.match(/^[\-\*]\s+(.*)/);
      if (listMatch) {
        if (!inList) {
          htmlLines.push("<ul>");
          inList = true;
        }
        let content = listMatch[1];
        // Parse bold and inline code inside list items
        content = content
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
          .replace(/`([^`]+)`/g, "<code>$1</code>");
        htmlLines.push(`<li>${content}</li>`);
        continue;
      } else {
        if (inList) {
          htmlLines.push("</ul>");
          inList = false;
        }
      }

      // Headers
      if (line.startsWith("### ")) {
        htmlLines.push(`<h3>${line.substring(4)}</h3>`);
      } else if (line.startsWith("## ")) {
        htmlLines.push(`<h2>${line.substring(3)}</h2>`);
      } else if (line.startsWith("# ")) {
        htmlLines.push(`<h1>${line.substring(2)}</h1>`);
      }
      // Blockquotes
      else if (line.startsWith("> ")) {
        htmlLines.push(`<blockquote>${line.substring(2)}</blockquote>`);
      }
      // Blank lines or paragraphs
      else {
        let content = line.trim();
        if (content) {
          // Parse bold and inline code in paragraphs
          content = content
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");
          htmlLines.push(`<p>${content}</p>`);
        } else {
          // Keep paragraph separation
          htmlLines.push("<br />");
        }
      }
    }

    // Close open list if still open
    if (inList) {
      htmlLines.push("</ul>");
    }

    // Close open code block if still open
    if (inCodeBlock) {
      htmlLines.push(`<pre><code>${codeContent.join("\n")}</code></pre>`);
    }

    return htmlLines.join("\n").replace(/(<br \/>\s*){2,}/g, "<br />");
  };

  const isPlaceholderMessage = status === "API_KEY_MISSING";
  const isErrorMessage = status === "CONNECTION_ERROR" || status === "error";

  return (
    <>
      {/* Decorative Orbs */}
      <div className="glow-orb-1"></div>
      <div className="glow-orb-2"></div>

      <div className="app-container">
        {/* Header */}
        <header className="app-header">
          <h1 className="app-title-gradient">Research Assistant</h1>
          <p className="app-subtitle">
            Autonomous multi-agent system powered by Groq and LangGraph. Ask anything
            to trigger deep research orchestration.
          </p>
        </header>

        {/* Search Panel */}
        <main className="glass-panel">
          <form onSubmit={handleResearch} className="search-form">
            <div className="search-input-wrapper">
              <input
                type="text"
                id="research-query-input"
                className="search-input"
                placeholder="Enter your research topic (e.g. 'Synthesize the latest breakthroughs in fusion energy research'...)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
                autoFocus
              />
            </div>

            <button
              type="submit"
              id="research-submit-button"
              className="btn-primary"
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <>Launching Agents...</>
              ) : (
                <>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  Analyze Topic
                </>
              )}
            </button>
          </form>

          {/* Loading State */}
          {loading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p className="loading-text">Spawning orchestrator and query engines...</p>
            </div>
          )}

          {/* Response Container */}
          {response && !loading && (
            <section
              className={`results-card glass-panel`}
              style={{
                marginTop: "2.5rem",
                padding: "2rem",
                borderLeft: isPlaceholderMessage
                  ? "4px solid var(--warning)"
                  : isErrorMessage
                    ? "4px solid var(--error)"
                    : "4px solid var(--success)",
                background: "rgba(10, 10, 20, 0.45)"
              }}
            >
              <div className="results-header">
                <h3 className="results-title">
                  {isPlaceholderMessage && (
                    <span style={{ color: "var(--warning)" }}>Setup Required</span>
                  )}
                  {isErrorMessage && (
                    <span style={{ color: "var(--error)" }}>Error Encountered</span>
                  )}
                  {!isPlaceholderMessage && !isErrorMessage && (
                    <>
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--success)"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{ marginRight: "0.25rem" }}
                      >
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                      Research Completed
                    </>
                  )}
                </h3>
                {modelUsed && modelUsed !== "None" && (
                  <span className="results-badge">{modelUsed}</span>
                )}
              </div>

              <div
                className="response-content"
                dangerouslySetInnerHTML={{ __html: parseMarkdown(response) }}
              />
            </section>
          )}
        </main>

        {/* Footer */}
        <footer className="app-footer">
          <p>
            Multi-Agent Research Assistant Portfolio Project. Powered by{" "}
            <a href="https://groq.com/" target="_blank" rel="noreferrer">Groq</a>,{" "}
            <a href="https://fastapi.tiangolo.com/" target="_blank" rel="noreferrer">FastAPI</a>, and{" "}
            <a href="https://nextjs.org/" target="_blank" rel="noreferrer">Next.js</a>.
          </p>
        </footer>
      </div>
    </>
  );
}
