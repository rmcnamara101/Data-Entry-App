import React, { useState, useEffect } from 'react';

const FolderScanner = () => {
  const [folderInfo, setFolderInfo] = useState(null);
  const [folderPath, setFolderPath] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentAction, setCurrentAction] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFolderStats = async () => {
      try {
        const response = await fetch('http://127.0.0.1:5000/api/patient-records', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
        if (response.ok) {
          const data = await response.json();
          setFolderInfo({
            total_images: data.records.length,
            processed_images: data.records.length
          });
        } else {
          throw new Error('Failed to fetch folder stats');
        }
      } catch (err) {
        console.error('Error fetching folder stats:', err);
        setFolderInfo({ total_images: 0, processed_images: 0 });
      }
    };

    fetchFolderStats();
  }, [result]); // Refresh stats when result changes

  const handleNewFolderSelect = (event) => {
    const files = Array.from(event.target.files);
  
    if (files.length === 0) {
      setFolderPath('');
      setSelectedFiles([]);
      setError('No folder selected!');
      return;
    }
  
    try {
      const firstFilePath = files[0].webkitRelativePath;
      const folderName = firstFilePath.split('/')[0];
      
      setFolderPath(folderName);
      setSelectedFiles(files);
      setError(null);
      setResult(null);
    } catch (error) {
      console.error('Error selecting folder:', error);
      setError('Unable to select folder. Ensure browser supports directory upload.');
    }
  };

  const scanDefaultFolder = async () => {
    setProcessing(true);
    setProgress(10);
    setResult(null);
    setError(null);
    setCurrentAction('Scanning default folder...');
  
    try {
      const response = await fetch('http://127.0.0.1:5000/api/scan-default-folder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({}) // Send empty object as body
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to scan default folder');
      }
  
      const data = await response.json();
      setProgress(100);
      setResult(data);
      setCurrentAction('Scan completed');
    } catch (err) {
      console.error('Error scanning default folder:', err);
      setError(err.message);
      setCurrentAction('Error occurred');
    } finally {
      setTimeout(() => {
        setProcessing(false);
        setProgress(0);
        setCurrentAction('');
      }, 1000);
    }
  };

  const scanNewFolder = async () => {
    if (!folderPath || selectedFiles.length === 0) {
      setError('Please select a folder with files first.');
      return;
    }
  
    setProcessing(true);
    setProgress(0);
    setResult(null);
    setError(null);
    setCurrentAction('Uploading files...');
  
    try {
      const formData = new FormData();
      formData.append('folder_path', folderPath);
      
      let totalSize = 0;
      let uploadedSize = 0;
      selectedFiles.forEach(file => {
        totalSize += file.size;
      });

      selectedFiles.forEach((file, index) => {
        formData.append('files[]', file);
        formData.append('relative_paths[]', file.webkitRelativePath);
        uploadedSize += file.size;
        const uploadProgress = (uploadedSize / totalSize) * 50;
        setProgress(Math.round(uploadProgress));
      });

      setCurrentAction('Processing files...');
      
      const response = await fetch('http://127.0.0.1:5000/api/scan-new-folder', {
        method: 'POST',
        body: formData,
      });
  
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to scan selected folder');
      }
  
      setProgress(75);
      setCurrentAction('Finalizing...');
      
      const data = await response.json();
      setProgress(100);
      setResult(data);
      setCurrentAction('Completed');
      
    } catch (err) {
      console.error('Error scanning new folder:', err);
      setError(err.message);
      setCurrentAction('Error occurred');
    } finally {
      setTimeout(() => {
        setProcessing(false);
        setProgress(0);
        setCurrentAction('');
      }, 1000);
    }
  };

  return (
    <div className="bg-gray-50 p-8 rounded-lg shadow-lg max-w-5xl mx-auto space-y-8">
      <div className="bg-blue-100 p-6 rounded-lg shadow-inner flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-blue-800">Folder Information</h2>
          <p className="text-blue-700 mt-2">
            Total Files in Database: {folderInfo?.total_images ?? 'Loading...'}
          </p>
          <p className="text-blue-700">
            Processed Files: {folderInfo?.processed_images ?? 'Loading...'}
          </p>
          {selectedFiles.length > 0 && (
            <p className="text-blue-700">Selected Files: {selectedFiles.length}</p>
          )}
        </div>
      </div>

      <div className="space-y-4">
        <button
          onClick={scanDefaultFolder}
          className={`w-full px-6 py-4 bg-green-500 text-white text-lg font-semibold rounded-lg shadow-lg hover:bg-green-600 transition-colors ${
            processing ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          disabled={processing}
        >
          {processing ? 'Scanning Default Folder...' : 'Scan Default Folder'}
        </button>

        <div className="relative">
          <input
            type="file"
            webkitdirectory="true"
            directory="true"
            id="new-folder-input"
            className="hidden"
            onChange={handleNewFolderSelect}
            disabled={processing}
          />
          <label
            htmlFor="new-folder-input"
            className={`w-full block px-6 py-4 bg-purple-500 text-white text-lg font-semibold text-center rounded-lg shadow-lg cursor-pointer hover:bg-purple-600 transition-colors ${
              processing ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {folderPath ? `Selected: ${folderPath}` : 'Select New Folder'}
          </label>
        </div>

        <button
          onClick={scanNewFolder}
          className={`w-full px-6 py-4 bg-blue-500 text-white text-lg font-semibold rounded-lg shadow-lg hover:bg-blue-600 transition-colors ${
            processing || !folderPath ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          disabled={processing || !folderPath}
        >
          {processing ? 'Scanning Selected Folder...' : 'Scan Selected Folder'}
        </button>
      </div>

      {processing && (
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-600">{currentAction}</span>
            <span className="text-sm font-medium text-gray-600">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-green-800">Scan Completed Successfully</h3>
              <div className="mt-2 text-green-700">
                <p>Total Files: {result.total_images}</p>
                <p>Records Added: {result.records_added}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-800">Error</h3>
              <p className="mt-2 text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FolderScanner;