import { useState, useEffect } from 'react';
import { checkHealth } from '../services/api';

export function useHealth() {
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    const check = async () => {
      try {
        await checkHealth();
        setStatus('online');
      } catch {
        setStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return status;
}
