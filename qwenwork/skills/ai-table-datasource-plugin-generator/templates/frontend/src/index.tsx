import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from '@ali/we-design-3';
import '@ali/we-design-3/default.css';
import '@ali/we-design-3/locale/zh-CN';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <Provider value={{ locale: 'zh-CN', colorScheme: 'light' }}>
      <App />
    </Provider>
  </React.StrictMode>
);
