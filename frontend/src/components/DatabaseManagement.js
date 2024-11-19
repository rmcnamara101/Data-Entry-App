import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Database, RefreshCw, Archive, AlertTriangle } from 'lucide-react';


const DatabaseManagement = () => {
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [lastBackup, setLastBackup] = useState(null);

  const handleBackup = async () => {
    setIsBackingUp(true);
    try {
      const response = await fetch('/api/backup-database', {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        setLastBackup(new Date().toLocaleString());
      }
    } catch (error) {
      console.error('Backup failed:', error);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleOptimize = async () => {
    setIsOptimizing(true);
    try {
      await fetch('/api/optimize-database', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Optimization failed:', error);
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Database Management</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Archive className="h-5 w-5" />
              <span>Backup Database</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-gray-600">
                Create a backup of the current database state. This includes all patient records
                and processing history.
              </p>
              {lastBackup && (
                <p className="text-sm text-gray-500">
                  Last backup: {lastBackup}
                </p>
              )}
              <button
                onClick={handleBackup}
                disabled={isBackingUp}
                className="w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 
                         disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
              >
                {isBackingUp ? (
                  <span className="flex items-center justify-center">
                    <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                    Backing up...
                  </span>
                ) : (
                  'Create Backup'
                )}
              </button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Database className="h-5 w-5" />
              <span>Optimize Database</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-gray-600">
                Optimize the database for better performance. This process may take a few minutes.
              </p>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-500" />
                  <p className="text-sm text-yellow-700">
                    Ensure all processing jobs are complete before optimization.
                  </p>
                </div>
              </div>
              <button
                onClick={handleOptimize}
                disabled={isOptimizing}
                className="w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 
                         disabled:bg-green-300 disabled:cursor-not-allowed transition-colors"
              >
                {isOptimizing ? (
                  <span className="flex items-center justify-center">
                    <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                    Optimizing...
                  </span>
                ) : (
                  'Optimize Database'
                )}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DatabaseManagement;