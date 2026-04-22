import { useState } from 'react';
import styles from './EmailInput.module.css';
import { processEmail } from '../services/api';

const SAMPLES = [
  {
    label: 'Lead',
    text: `Subject: Enterprise License Inquiry\n\nHi team,\n\nI'm Sarah Chen, CTO at NexaCloud Inc. We're evaluating sales automation tools for our 200-person sales org.\n\nCould we schedule a 30-min call this week?\n\nBest,\nSarah`,
  },
  {
    label: 'Complaint',
    text: `Subject: Billing Issue - Urgent\n\nHello,\n\nMy name is John Martin, customer ID #4821. I was charged twice for my subscription this month ($299 x2).\n\nThis is the third billing error in two months. I need this resolved immediately or I'll dispute the charges.\n\nJohn`,
  },
  {
    label: 'Spam',
    text: `Subject: YOU HAVE WON $1,000,000!!!\n\nDear Winner,\n\nCongratulations! You have been selected to receive ONE MILLION DOLLARS. Click the link below to claim your prize NOW!!!\n\nwww.totally-legit-prizes.com/claim`,
  },
];

export default function EmailInput({ onResult, onLoading, threadId }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    onLoading(true);

    try {
      const res = await processEmail(text, threadId);
      onResult({ ...res.data, emailText: text });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Pipeline failed. Is the backend running?';
      setError(msg);
    } finally {
      setLoading(false);
      onLoading(false);
    }
  };

  const handleSample = (sample) => {
    setText(sample.text);
    setError(null);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Inbound Email Processor</h1>
          <p className={styles.sub}>Paste an email below and run the multi-agent pipeline.</p>
        </div>
        <div className={styles.samples}>
          {SAMPLES.map((s) => (
            <button key={s.label} className={styles.sampleBtn} onClick={() => handleSample(s)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.inputWrapper}>
        <textarea
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={'Subject: Enterprise License Inquiry\n\nHi team, I\'m the CTO at Acme Corp and we\'re looking for...'}
          spellCheck={false}
        />
        <div className={styles.inputFooter}>
          <span className={styles.charCount}>{text.length} chars</span>
          <button
            className={`${styles.runBtn} ${loading ? styles.loading : ''}`}
            onClick={handleSubmit}
            disabled={loading || !text.trim()}
            id="run-pipeline-btn"
          >
            {loading ? (
              <>
                <span className={styles.spinner} />
                Running Pipeline...
              </>
            ) : (
              <>
                <span>🚀</span>
                Run Agent Pipeline
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className={styles.error}>
          <span>⚠️</span> {error}
        </div>
      )}
    </div>
  );
}
