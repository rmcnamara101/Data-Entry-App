import React, { useState, useEffect } from 'react';

const FolderScanner = () => {
  const [folderInfo, setFolderInfo] = useState(null);
  const [folderPath, setFolderPath] = useState('');
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Fetch default folder stats
  useEffect(() => {
    const fetchFolderStats = async () => {
      try {
        const response = await fetch('/api/folder-stats', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder_path: '/path/to/default/folder' }),
        });
        if (response.ok) {
          const data = await response.json();
          setFolderInfo(data);
        } else {
          setFolderInfo({ total_images: 0, processed_images: 0 });
        }
      } catch (err) {
        console.error('Error fetching folder stats:', err);
        setFolderInfo({ total_images: 0, processed_images: 0 });
      }
    };

    fetchFolderStats();
  }, []);

  const handleNewFolderSelect = (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) {
      setFolderPath('');
      alert('No folder selected!');
      return;
    }

    const folderName = files[0].webkitRelativePath.split('/')[0];
    setFolderPath(folderName);
    setResult(null);
    setError(null);
  };

  const scanDefaultFolder = async () => {
    setProcessing(true);
    setProgress(10);
    setResult(null);
    setError(null);

    try {
      const response = await fetch('/api/scan-default-folder', {
        method: 'POST',
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to scan default folder.');
      }

      const data = await response.json();
      setProgress(100);
      setResult(data);
    } catch (err) {
      console.error('Error scanning default folder:', err);
      setError(err.message);
    } finally {
      setProcessing(false);
      setProgress(0);
    }
  };

  const scanNewFolder = async () => {
    if (!folderPath) {
      alert('Please select a folder first.');
      return;
    }

    setProcessing(true);
    setProgress(10);
    setResult(null);
    setError(null);

    try {
      const response = await fetch('/api/scan-new-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to scan selected folder.');
      }

      const data = await response.json();
      setProgress(100);
      setResult(data);
    } catch (err) {
      console.error('Error scanning new folder:', err);
      setError(err.message);
    } finally {
      setProcessing(false);
      setProgress(0);
    }
  };

  return (
    <div className="bg-gray-50 p-8 rounded-lg shadow-lg max-w-5xl mx-auto space-y-8">
      <div className="bg-blue-100 p-6 rounded-lg shadow-inner flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-blue-800">Folder Information</h2>
          <p className="text-blue-700 mt-2">
            Total Files: {folderInfo?.total_images ?? 'Loading...'}
          </p>
          <p className="text-blue-700">Processed Files: {folderInfo?.processed_images ?? 'Loading...'}</p>
        </div>
      </div>

      <div className="space-y-4">
        <button
          onClick={scanDefaultFolder}
          className={`w-full px-6 py-4 bg-green-500 text-white text-lg font-semibold rounded-lg shadow-lg hover:bg-green-600 ${
            processing && 'opacity-50 cursor-not-allowed'
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
          />
          <label
            htmlFor="new-folder-input"
            className={`w-full block px-6 py-4 bg-purple-500 text-white text-lg font-semibold text-center rounded-lg shadow-lg cursor-pointer hover:bg-purple-600`}
          >
            {folderPath ? `Selected Folder: ${folderPath}` : 'Select New Folder'}
          </label>
        </div>

        <button
          onClick={scanNewFolder}
          className={`w-full px-6 py-4 bg-blue-500 text-white text-lg font-semibold rounded-lg shadow-lg hover:bg-blue-600 ${
            processing || !folderPath ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          disabled={processing || !folderPath}
        >
          {processing ? 'Scanning Selected Folder...' : 'Scan Selected Folder'}
        </button>
      </div>

      {processing && (
        <div className="w-full bg-gray-200 rounded-lg h-4 mt-6">
          <div
            className="bg-blue-500 h-4 rounded-lg transition-all"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}

      {result && (
        <div className="bg-green-100 p-6 rounded-lg shadow-inner mt-6">
          <h3 className="text-lg font-bold text-green-800">Scan Completed</h3>
          <p className="text-green-700 mt-2">Total Files: {result.total_images}</p>
          <p className="text-green-700">Records Added: {result.records_added}</p>
        </div>
      )}

      {error && (
        <div className="bg-red-100 p-6 rounded-lg shadow-inner mt-6">
          <h3 className="text-lg font-bold text-red-800">Error</h3>
          <p className="text-red-700 mt-2">{error}</p>
        </div>
      )}
    </div>
  );
};

export default FolderScanner;