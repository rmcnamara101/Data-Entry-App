import React from 'react';
import Dashboard from './Dashboard';
import FolderScanner from './FolderScanner';
import BatchProcessing from './BatchProcessing';
import DatabaseManagement from './DatabaseManagement';
import Settings from './Settings';

const MainContent = ({ activeView }) => { // Accept activeView prop
  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <Dashboard />;
      case 'folderScan':
        return <FolderScanner />;
      case 'batchScan':
        return <BatchProcessing />;
      case 'database':
        return <DatabaseManagement />;
      case 'settings':
        return <Settings />;
      default:
        return null;
    }
  };

  return <div>{renderView()}</div>;
};

export default MainContent;