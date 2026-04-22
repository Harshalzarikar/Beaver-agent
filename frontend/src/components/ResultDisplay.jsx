import styles from './ResultDisplay.module.css';
import StatusBadge from './StatusBadge';

export default function ResultDisplay({ result }) {
  if (!result) return (
    <div className={styles.empty}>
      <div className={styles.emptyIcon}>⏳</div>
      <div className={styles.emptyText}>Waiting for input...</div>
      <div className={styles.emptySub}>The agent pipeline results will appear here.</div>
    </div>
  );

  const { category, company, revisions, time_ms, draft, trace } = result;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.mainInfo}>
          <div className={styles.label}>Classification</div>
          <StatusBadge category={category} />
        </div>
        <div className={styles.metrics}>
          <div className={styles.metric}>
            <div className={styles.mLabel}>Company</div>
            <div className={styles.mValue}>{company || 'N/A'}</div>
          </div>
          <div className={styles.metric}>
            <div className={styles.mLabel}>Revisions</div>
            <div className={styles.mValue}>{revisions}</div>
          </div>
          <div className={styles.metric}>
            <div className={styles.mLabel}>Latence</div>
            <div className={styles.mValue}>{time_ms}ms</div>
          </div>
        </div>
      </div>

      <div className={styles.content}>
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitle}>✍️ Generated Draft</div>
            <button 
              className={styles.copyBtn}
              onClick={() => navigator.clipboard.writeText(draft)}
            >
              Copy
            </button>
          </div>
          <div className={styles.draftBox}>
            {draft}
          </div>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionTitle}>🕵️ Execution Trace</div>
          <div className={styles.traceList}>
            {trace.map((step, i) => (
              <div key={i} className={styles.traceItem}>
                <span className={styles.traceDot} />
                <span className={styles.traceText}>{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
