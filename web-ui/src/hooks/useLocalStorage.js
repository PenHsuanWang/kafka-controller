import React from 'react';

export default function useLocalStorage(key, initial) {
  const [state, setState] = React.useState(() => {
    const raw = localStorage.getItem(key);
    try {
      return raw ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });
  const set = (v) => {
    setState(v);
    localStorage.setItem(key, JSON.stringify(v));
  };
  return [state, set];
}
