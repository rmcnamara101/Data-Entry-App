// src/App.js

import React, { useState } from 'react';
import MainContent from './components/MainContent';
import SideNavigation from './components/SideNavigation';

function App() {
  const [activeView, setActiveView] = useState('dashboard'); // Set default to 'dashboard'

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Side Navigation */}
      <SideNavigation activeView={activeView} setActiveView={setActiveView} />

      {/* Main Content */}
      <MainContent activeView={activeView} setActiveView={setActiveView} />
    </div>
  );
}

export default App;