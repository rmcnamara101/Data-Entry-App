// src/components/MainContent.js

import React from 'react';
import Dashboard from './Dashboard';
import FolderProcessor from './FolderProcessor';
import BatchProcessing from './BatchProcessing';
import DatabaseManagement from './DatabaseManagement';
import Protocols from './Protocols';
import InputData from './InputData';
import Settings from './Settings';

const MainContent = ({ activeView, setActiveView }) => {
  const renderContent = () => {
    switch (activeView) {
      case 'dashboard':
        return <Dashboard setActiveView={setActiveView} />;
      case 'folderScan':
        return <FolderProcessor />;
      case 'batchScan':
        return <BatchProcessing />;
      case 'database':
        return <DatabaseManagement />;
      case 'protocols':
        return <Protocols />;
      case 'inputData':
        return <InputData />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard setActiveView={setActiveView} />;
    }
  };

  return (
    <div className="flex-1 overflow-auto">
      {renderContent()}
    </div>
  );
};

export default MainContent;