import React from 'react';
import FolderProcessor from './components/FolderProcessor';
import DatabaseManagement from './components/DatabaseManagement';
import PatientRecordsDashboard from './components/PatientRecordsDashboard';

const MainContent = ({ activeView }) => {
  const renderContent = () => {
    switch (activeView) {
      case 'dashboard':
        return <PatientRecordsDashboard />;
      case 'upload':
        return <FolderProcessor />;
      case 'database':
        return <DatabaseManagement />;
      default:
        return <PatientRecordsDashboard />;
    }
  };

  return (
    <div className="h-full">
      {renderContent()}
    </div>
  );
};

export default MainContent;