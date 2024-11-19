import React from 'react';
import { Layout, Upload, Database } from 'lucide-react';

const SideNavigation = ({ activeView, setActiveView }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Layout },
    { id: 'upload', label: 'Upload Forms', icon: Upload },
    { id: 'database', label: 'Database', icon: Database },
  ];

  return (
    <nav className="fixed left-0 top-0 bottom-0 w-64 bg-white shadow-lg">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-800">Pathology Lab</h1>
      </div>
      <ul className="space-y-2 px-4">
        {navItems.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => setActiveView(item.id)}
              className={`w-full flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                activeView === item.id
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default SideNavigation;