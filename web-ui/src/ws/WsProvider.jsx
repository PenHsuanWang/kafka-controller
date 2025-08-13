import React from 'react';

export const WsContext = React.createContext({ kpis: undefined, connected: false });

export function WsProvider({ children }) {
  const [kpis, setKpis] = React.useState();
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const local = (() => {
      try { return JSON.parse(localStorage.getItem('wsUrl')); } catch { return null; }
    })();
    const url = local || process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws/v1/stream';

    let ws;
    try {
      ws = new WebSocket(url);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg?.channel === 'cluster' && msg?.event === 'kpi.update') {
            setKpis(msg.data);
          }
        } catch { /* ignore */ }
      };
    } catch {
      setConnected(false);
    }
    return () => ws && ws.close();
  }, []);

  return (
    <WsContext.Provider value={{ kpis, connected }}>
      {children}
    </WsContext.Provider>
  );
}
