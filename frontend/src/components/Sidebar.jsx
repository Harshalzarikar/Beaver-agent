import styles from './Sidebar.module.css';
import { useHealth } from '../hooks/useHealth';

const AGENTS = [
  { icon: '🚦', name: 'Router', desc: 'Email Classification' },
  { icon: '🔍', name: 'Researcher', desc: 'Company Intelligence' },
  { icon: '✍️', name: 'Writer', desc: 'Draft Generation' },
  { icon: '⚖️', name: 'Verifier', desc: 'Quality Gate' },
  { icon: '🛡️', name: 'Support', desc: 'Complaint Handler' },
];

export default function Sidebar({ history, onSelectHistory }) {
  const health = useHealth();

  return (
    <aside className={styles.sidebar}>
      {/* Brand */}
      <div className={styles.brand}>
        <div className={styles.logo}>🦫</div>
        <div>
          <div className={styles.brandName}>Beaver Agent</div>
          <div className={styles.brandSub}>Multi-Agent Orchestrator</div>
        </div>
      </div>

      {/* Status */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>System Status</div>
        <div className={styles.statusRow}>
          <span className={`${styles.dot} ${styles[health]}`} />
          <span className={styles.statusText}>
            {health === 'checking' ? 'Connecting...' : health === 'online' ? 'Online' : 'Offline'}
          </span>
          <span className={styles.statusUrl}>:8000</span>
        </div>
      </div>

      {/* Agents */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Agent Pipeline</div>
        <div className={styles.agentList}>
          {AGENTS.map((a, i) => (
            <div key={i} className={styles.agentItem}>
              <span className={styles.agentIcon}>{a.icon}</span>
              <div>
                <div className={styles.agentName}>{a.name}</div>
                <div className={styles.agentDesc}>{a.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className={styles.section} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className={styles.sectionLabel}>Recent ({history.length})</div>
          <div className={styles.historyList}>
            {history.slice().reverse().map((item, i) => (
              <div key={i} className={styles.historyItem} onClick={() => onSelectHistory(item)}>
                <span className={`${styles.historyDot} ${styles[item.category?.toLowerCase()]}`} />
                <div className={styles.historyInfo}>
                  <div className={styles.historyCat}>{item.category}</div>
                  <div className={styles.historyComp}>{item.company || 'Unknown'}</div>
                </div>
                <div className={styles.historyTime}>{item.time_ms}ms</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={styles.footer}>v1.0.0 · Production</div>
    </aside>
  );
}
