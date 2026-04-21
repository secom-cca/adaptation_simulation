// 本地存储自定义Hook
import { useState, useEffect } from 'react';
import { storage } from '../utils/helpers';

export const useLocalStorage = (key, defaultValue) => {
  const [value, setValue] = useState(() => {
    const storedValue = storage.get(key);
    return storedValue !== null ? storedValue : defaultValue;
  });

  useEffect(() => {
    storage.set(key, value);
  }, [key, value]);

  return [value, setValue];
};
