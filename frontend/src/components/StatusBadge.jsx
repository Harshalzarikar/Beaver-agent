import styles from './StatusBadge.module.css';

const CONFIG = {
  Lead:      { label: 'Lead', color: 'lead' },
  Complaint: { label: 'Complaint', color: 'complaint' },
  Spam:      { label: 'Spam', color: 'spam' },
};

export default function StatusBadge({ category }) {
  const cfg = CONFIG[category] || { label: category, color: 'lead' };
  return (
    <span className={`${styles.badge} ${styles[cfg.color]}`}>
      {cfg.label}
    </span>
  );
}
