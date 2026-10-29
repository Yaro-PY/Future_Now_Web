import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.jsx';
import './styles.css';
import './sections.css';
import './responsive.css';

class ErrorBoundary extends React.Component {
  state = {failed: false};
  static getDerivedStateFromError() { return {failed: true}; }
  render() {
    if (this.state.failed) return <main className="boot-screen"><p>Не вдалося відкрити сторінку.</p><button className="button primary" onClick={() => location.reload()}>Спробувати ще раз</button></main>;
    return this.props.children;
  }
}

createRoot(document.getElementById('app')).render(<ErrorBoundary><App /></ErrorBoundary>);
