import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import IslandApp from './components/IslandApp';
import './index.css';

const isIslandWindow =
  typeof window !== 'undefined' &&
  new URLSearchParams(window.location.search).get('window') === 'island';

if (isIslandWindow && typeof document !== 'undefined') {
  document.documentElement.classList.add('island-mode');
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {isIslandWindow ? <IslandApp /> : <App />}
  </React.StrictMode>
);
