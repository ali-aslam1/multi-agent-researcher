"use client";

import React, { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  // Pipeline stage tracking
  // Stages: "idle" | "decomposing" | "searching" | "summarizing" | "critiquing" | "aggregating" | "completed" | "error" | "api_key_missing"
  const [currentStage, setCurrentStage] = useState("idle");
  const [sourceUrls, setSourceUrls] = useState([]);
  const [streamingReport, setStreamingReport] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setCurrentStage("decomposing");
    setSourceUrls([]);
    setStreamingReport("");
    setErrorMsg("");

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

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          buffer += decoder.decode(value, { stream: !done });

          // Split buffer by SSE event boundaries (double newline)
          const parts = buffer.split("\n\n");
          // Keep the last part as buffer in case it is incomplete
          buffer = parts.pop() || "";

          for (const part of parts) {
            const line = part.trim();
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.substring(6));

                if (data.type === "status") {
                  if (data.status === "decomposed") {
                    setCurrentStage("searching");
                  } else if (data.status === "searched") {
                    setSourceUrls(data.source_urls);
                    setCurrentStage("summarizing");
                  } else if (data.status === "summarized") {
                    setCurrentStage("critiquing");
                  } else if (data.status === "critiqued") {
                    setCurrentStage("aggregating");
                  } else if (data.status === "completed") {
                    if (data.final_report) {
                      setStreamingReport(data.final_report);
                    }
                    setCurrentStage("completed");
                  } else if (data.status === "error") {
                    setErrorMsg(data.message);
                    setCurrentStage("error");
                  } else if (data.status === "API_KEY_MISSING") {
                    setErrorMsg(data.message);
                    setCurrentStage("api_key_missing");
                  }
                }
              } catch (err) {
                console.error("Error parsing stream chunk:", err, line);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(
        `Failed to connect to the backend server.\n\n` +
        `Technical Details:\n${err.message || err}`
      );
      setCurrentStage("error");
    } finally {
      setLoading(false);
    }
  };

  // Modern, robust Vanilla JS markdown parser for instant styled HTML rendering
  const parseMarkdown = (text) => {
    if (!text) return "";

    // Process markdown line-by-line for precise structure
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

    if (inList) htmlLines.push("</ul>");
    if (inCodeBlock) htmlLines.push(`<pre><code>${codeContent.join("\n")}</code></pre>`);

    return htmlLines.join("\n").replace(/(<br \/>\s*){2,}/g, "<br />");
  };

  const getStageStatus = (stageName) => {
    const order = ["decomposing", "searching", "summarizing", "critiquing", "aggregating", "completed"];
    const currentIdx = order.indexOf(currentStage);
    const targetIdx = order.indexOf(stageName);

    if (currentStage === "error" || currentStage === "api_key_missing") {
      return "completed"; // freeze state
    }

    if (currentIdx > targetIdx) return "completed";
    if (currentIdx === targetIdx) return "active";
    return "pending";
  };

  const getStageIcon = (status) => {
    if (status === "completed") return <span className="stage-icon completed">✓</span>;
    if (status === "active") return <span className="stage-icon active">●</span>;
    return <span className="stage-icon pending">○</span>;
  };

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
            Ask anything. Multiple agents search, summarize, and compile a report.
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
                placeholder="Ask a question or enter a topic to research..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
                autoFocus
                required
              />
            </div>

            <button
              type="submit"
              id="research-submit-button"
              className="btn-primary"
              disabled={loading}
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
                  Research
                </>
              )}
            </button>
          </form>

          {/* Pipeline Tracker */}
          {currentStage !== "idle" && (
            <section style={{ marginTop: "2.5rem" }}>
              <h3 style={{ marginBottom: "1.5rem", fontWeight: "700" }}>Research Progress</h3>
              <div className="pipeline-stages">

                {/* Stage 1: Decomposition */}
                <div className={`stage-card ${getStageStatus("decomposing")}`}>
                  <div className="stage-header">
                    {getStageIcon(getStageStatus("decomposing"))}
                    <span className="stage-title">Planning</span>
                    <span className="stage-subtitle">Breaking your question into smaller parts</span>
                  </div>
                </div>

                {/* Stage 2: Web Search */}
                <div className={`stage-card ${getStageStatus("searching")}`}>
                  <div className="stage-header">
                    {getStageIcon(getStageStatus("searching"))}
                    <span className="stage-title">Searching</span>
                    <span className="stage-subtitle">Searching the web for relevant sources</span>
                  </div>
                </div>

                {/* Stage 3: Summarization */}
                <div className={`stage-card ${getStageStatus("summarizing")}`}>
                  <div className="stage-header">
                    {getStageIcon(getStageStatus("summarizing"))}
                    <span className="stage-title">Summarizing</span>
                    <span className="stage-subtitle">Reading and summarizing sources</span>
                  </div>
                </div>

                {/* Stage 4: Critic */}
                <div className={`stage-card ${getStageStatus("critiquing")}`}>
                  <div className="stage-header">
                    {getStageIcon(getStageStatus("critiquing"))}
                    <span className="stage-title">Fact-checking</span>
                    <span className="stage-subtitle">Checking for conflicts between sources</span>
                  </div>
                </div>

                {/* Stage 5: Aggregator */}
                <div className={`stage-card ${getStageStatus("aggregating")}`}>
                  <div className="stage-header">
                    {getStageIcon(getStageStatus("aggregating"))}
                    <span className="stage-title">Writing report</span>
                    <span className="stage-subtitle">Compiling everything into a final report</span>
                  </div>
                </div>

              </div>
            </section>
          )}

          {/* Setup / Error Message Cards */}
          {(currentStage === "error" || currentStage === "api_key_missing") && (
            <section
              className="results-card glass-panel"
              style={{
                borderLeft: currentStage === "api_key_missing" ? "4px solid var(--warning)" : "4px solid var(--error)",
                background: "rgba(10, 10, 20, 0.45)",
                padding: "2rem"
              }}
            >
              <h3 className="results-title">
                {currentStage === "api_key_missing" ? (
                  <span style={{ color: "var(--warning)" }}>Setup Required</span>
                ) : (
                  <span style={{ color: "var(--error)" }}>Error Encountered</span>
                )}
              </h3>
              <div
                className="response-content"
                style={{ marginTop: "1rem" }}
                dangerouslySetInnerHTML={{ __html: parseMarkdown(errorMsg) }}
              />
            </section>
          )}

          {/* Streaming Final Report Response Container */}
          {(streamingReport || currentStage === "completed") && (
            <section
              className="results-card glass-panel"
              style={{
                marginTop: "2.5rem",
                padding: "2.5rem",
                borderLeft: "4px solid var(--success)",
                background: "rgba(10, 10, 20, 0.45)"
              }}
            >
              <div className="results-header">
                <h3 className="results-title">
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
                  {currentStage === "aggregating" ? "Writing report..." : "Research Report"}
                </h3>
                <span className="results-badge">llama-3.3-70b-versatile</span>
              </div>

              {/* Main report body */}
              <div className="response-content">
                <div dangerouslySetInnerHTML={{ __html: parseMarkdown(streamingReport) }} style={{ display: "inline" }} />
              </div>

              {/* Sources Section */}
              {sourceUrls && sourceUrls.length > 0 && (
                <div className="sources-container">
                  <h4 className="sources-heading">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                    </svg>
                    Sources
                  </h4>
                  <ul className="sources-list">
                    {sourceUrls.map((src, i) => (
                      <li key={i} className="source-item">
                        <span className="source-number">[{i + 1}]</span>
                        <a href={src.url} target="_blank" rel="noreferrer" className="source-link" title={src.title}>
                          {src.title || src.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}
        </main>

        {/* Footer */}
        <footer className="app-footer">
          <p>
            Built with{" "}
            <a href="https://groq.com/" target="_blank" rel="noreferrer">Groq</a>,{" "}
            <a href="https://fastapi.tiangolo.com/" target="_blank" rel="noreferrer">FastAPI</a>, and{" "}
            <a href="https://nextjs.org/" target="_blank" rel="noreferrer">Next.js</a>.
          </p>
        </footer>
      </div>
    </>
  );
}
