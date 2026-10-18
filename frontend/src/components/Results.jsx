import { useRef } from "react";
import { Notice, Spinner } from "./Feedback.jsx";

function SummaryTab({ analysis }) {
  const { summary, stats } = analysis;
  return (
    <div>
      <Notice message={summary.warning} />
      <p className="summary-text">{summary.summary}</p>
      <dl className="stats">
        <div>
          <dt>Words</dt>
          <dd>{stats.words}</dd>
        </div>
        <div>
          <dt>Sentences</dt>
          <dd>{stats.sentences}</dd>
        </div>
        <div>
          <dt>Fillers removed</dt>
          <dd>{stats.fillers_removed}</dd>
        </div>
        <div>
          <dt>Unique terms</dt>
          <dd>{stats.unique_terms}</dd>
        </div>
      </dl>
      <p className="muted small">Method: {summary.method}</p>
    </div>
  );
}

function KeywordsTab({ analysis }) {
  const { keywords } = analysis;
  if (!keywords.length) return <p className="muted">No keywords were found in this text.</p>;
  return (
    <div>
      <ul className="keywords">
        {keywords.map((k) => (
          <li key={k.keyword}>
            <span className="kw-name">{k.keyword}</span>
            <span className="kw-bar" aria-hidden="true">
              <span style={{ width: `${Math.round(k.relevance * 100)}%` }} />
            </span>
            <span className="kw-score">{Math.round(k.relevance * 100)}%</span>
          </li>
        ))}
      </ul>
      <p className="muted small">
        Extracted with {keywords[0].method.toUpperCase()}. A higher percentage means a more
        relevant term.
      </p>
    </div>
  );
}

function ActionsTab({ analysis }) {
  const items = analysis.action_items;
  if (!items.length)
    return (
      <p className="muted">
        No action items detected. They are found in sentences like &ldquo;Priya will send the
        report by Friday&rdquo; or &ldquo;We need to fix the login bug.&rdquo;
      </p>
    );
  return (
    <ul className="actions">
      {items.map((a, i) => (
        <li key={i}>
          <p className="action-task">{a.task}</p>
          <div className="chips">
            <span className="chip">Owner: {a.assignee}</span>
            <span className="chip">Deadline: {a.deadline || "none"}</span>
            {a.priority === "High" && <span className="chip chip-high">High priority</span>}
            <span className="chip chip-quiet">Confidence {Math.round(a.confidence * 100)}%</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function Results({
  analysis,
  tab,
  onTabChange,
  loading,
  onDownload,
  downloading,
}) {
  const tabRefs = useRef([]);
  const tabs = [
    { id: "summary", label: "Summary" },
    { id: "keywords", label: "Keywords", count: analysis?.keywords.length },
    { id: "actions", label: "Action items", count: analysis?.action_items.length },
  ];

  const onKeyDown = (e, index) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const next = (index + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    onTabChange(tabs[next].id);
    tabRefs.current[next]?.focus();
  };

  return (
    <section className="panel results" aria-labelledby="results-heading">
      <div className="panel-head">
        <h2 id="results-heading">Results</h2>
        <div className="row">
          <button
            className="btn btn-secondary"
            disabled={!analysis || !!downloading}
            onClick={() => onDownload("txt")}
          >
            {downloading === "txt" ? "Preparing..." : "Download TXT"}
          </button>
          <button
            className="btn btn-secondary"
            disabled={!analysis || !!downloading}
            onClick={() => onDownload("json")}
          >
            {downloading === "json" ? "Preparing..." : "Download JSON"}
          </button>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Analysis results">
        {tabs.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => (tabRefs.current[i] = el)}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            tabIndex={tab === t.id ? 0 : -1}
            className={`tab${tab === t.id ? " active" : ""}`}
            onClick={() => onTabChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {t.label}
            {analysis && t.count !== undefined && <span className="tab-count">{t.count}</span>}
          </button>
        ))}
      </div>

      <div
        className="tab-panel"
        role="tabpanel"
        id={`panel-${tab}`}
        aria-labelledby={`tab-${tab}`}
        tabIndex={0}
      >
        {loading ? (
          <Spinner label="Summarising and extracting keywords and action items. The first run can take a minute while the model loads." />
        ) : !analysis ? (
          <p className="muted">
            Upload or record audio and select <strong>Transcribe audio</strong>, or paste text
            into the transcript box and select <strong>Analyze text</strong>. Your summary,
            keywords and action items will appear here.
          </p>
        ) : tab === "summary" ? (
          <SummaryTab analysis={analysis} />
        ) : tab === "keywords" ? (
          <KeywordsTab analysis={analysis} />
        ) : (
          <ActionsTab analysis={analysis} />
        )}
      </div>
    </section>
  );
}
