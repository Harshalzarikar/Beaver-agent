import { useState } from 'react';
import styles from './App.module.css';
import Sidebar from './components/Sidebar';
import EmailInput from './components/EmailInput';
import ResultDisplay from './components/ResultDisplay';

function App() {
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize or retrieve thread_id for multi-user/multi-session tracking
  const [threadId] = useState(() => {
    const saved = sessionStorage.getItem('beaver_thread_id');
    if (saved) return saved;
    const newId = crypto.randomUUID();
    sessionStorage.setItem('beaver_thread_id', newId);
    return newId;
  });

  const handleResult = (data) => {
    setResult(data);
    setHistory(prev => [...prev, data]);
  };

  const handleSelectHistory = (item) => {
    setResult(item);
  };

  return (
    <div className={styles.app}>
      <Sidebar history={history} onSelectHistory={handleSelectHistory} />
      
      <main className={styles.main}>
        <div className={styles.content}>
          <div className={styles.left}>
            <EmailInput 
              onResult={handleResult} 
              onLoading={setIsLoading} 
              threadId={threadId} 
            />
            
            {isLoading && (
              <div className={styles.loadingOverlay}>
                <div className={styles.loader}>
                  <div className={styles.pulse} />
                  <div className={styles.pulse} style={{ animationDelay: '0.2s' }} />
                  <div className={styles.pulse} style={{ animationDelay: '0.4s' }} />
                </div>
                <div className={styles.loadingText}>Agents are working...</div>
              </div>
            )}
          </div>
          
          <div className={styles.right}>
            <ResultDisplay result={result} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
