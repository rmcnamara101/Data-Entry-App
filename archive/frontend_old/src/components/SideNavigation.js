// src/components/SideNavigation.js

import React from 'react';

const SideNavigation = ({ activeView, setActiveView }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'folderScan', label: 'Folder Scan' },
    { id: 'batchScan', label: 'Batch Scan' },
    { id: 'database', label: 'Database' },
    { id: 'protocols', label: 'Protocols' },
    { id: 'inputData', label: 'Input Data' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <nav className="w-64 bg-white shadow-lg flex flex-col">
      {/* Branding Section */}
      <div className="h-16 flex items-center justify-center border-b">
        <h1 className="text-xl font-bold text-gray-800">Pathology Lab</h1>
      </div>

      {/* Navigation Items */}
      <ul className="flex-1 px-4 py-6 space-y-4">
        {navItems.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => setActiveView(item.id)}
              className={`w-full text-left flex items-center px-4 py-2 rounded-lg transition-colors ${
                activeView === item.id
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <span className="ml-2">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default SideNavigation;