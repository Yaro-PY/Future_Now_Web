import {useCallback, useEffect, useState} from 'react';

export function useToast() {
  const [notification, setNotification] = useState(null);
  const toast = useCallback(message => setNotification({message,key:Date.now()}), []);
  useEffect(() => {
    if (!notification) return;
    const timer = setTimeout(() => setNotification(null), 4200);
    return () => clearTimeout(timer);
  }, [notification]);
  return {notification, toast};
}
