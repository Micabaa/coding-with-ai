import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import NavBar from './components/NavBar';
import SingingPage from './pages/SingingPage';
import LeaderboardPage from './pages/LeaderboardPage';
import ProfilePage from './pages/ProfilePage';
import ChatPage from './pages/ChatPage'; // New
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <div className="app-container">
          <NavBar />
          <div className="page-content">
            <Routes>
              <Route path="/" element={<SingingPage mode="casual" />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/competition" element={<SingingPage mode="competition" />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          </div>
        </div>
      </ErrorBoundary>
    </Router>
  );
}

export default App;
