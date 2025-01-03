// src/components/Dashboard.js

import React from 'react';

const Dashboard = ({ setActiveView }) => {
  return (
    <div className="dashboard-container p-8">
      <div className="logo-container mb-8 text-center">
        {/* Replace with your logo's path */}
        <img src="/path/to/your/logo.png" alt="Company Logo" className="mx-auto w-48 h-auto" />
      </div>
      <div className="button-grid grid grid-cols-2 gap-4">
        <button
          onClick={() => setActiveView('folderScan')}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Folder Scan
        </button>
        <button
          onClick={() => setActiveView('database')}
          className="bg-green-500 text-white px-4 py-2 rounded"
        >
          Database
        </button>
        <button
          onClick={() => setActiveView('batchScan')}
          className="bg-purple-500 text-white px-4 py-2 rounded"
        >
          Batch Scan
        </button>
        <button
          onClick={() => setActiveView('protocols')}
          className="bg-yellow-500 text-white px-4 py-2 rounded"
        >
          Protocols
        </button>
        <button
          onClick={() => setActiveView('inputData')}
          className="bg-indigo-500 text-white px-4 py-2 rounded"
        >
          Input Data
        </button>
        <button
          onClick={() => setActiveView('settings')}
          className="bg-red-500 text-white px-4 py-2 rounded"
        >
          Settings
        </button>
      </div>
    </div>
  );
};

export default Dashboard;