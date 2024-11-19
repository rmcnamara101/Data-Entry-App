import React, { useState } from 'react';
import { Folder, FileText, Database } from 'lucide-react';

const FolderProcessor = () => {
  const [folderPath, setFolderPath] = useState('');
  const [folderStats, setFolderStats] = useState(null);

  const handleFolderSelect = async (event) => {
    const selectedPath = event.target.files[0].path;
    setFolderPath(selectedPath);

    try {
      const response = await fetch('/api/folder-stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: selectedPath })
      });

      const stats = await response.json();
      setFolderStats(stats);
    } catch (error) {
      console.error('Error fetching folder stats:', error);
    }
  };

  const processFolderImages = async () => {
    try {
      const response = await fetch('/api/process-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath })
      });

      const result = await response.json();
      setFolderStats(result);
      alert('Folder processing complete!');
    } catch (error) {
      console.error('Error processing folder:', error);
    }
  };

  return (
    <div className="bg-white p-8 rounded-lg">
      <h2 className="text-2xl font-bold mb-6">Folder Processor</h2>
      
      <input 
        type="file" 
        webkitdirectory="true" 
        directory="true"
        onChange={handleFolderSelect}
        className="hidden" 
        id="folder-input"
      />
      <label 
        htmlFor="folder-input" 
        className="flex items-center justify-center w-full px-4 py-3 bg-blue-500 text-white rounded-md cursor-pointer hover:bg-blue-600 mb-4"
      >
        <Folder className="mr-2" />
        Select Request Forms Folder
      </label>

      {folderPath && (
        <div className="bg-gray-100 p-4 rounded-md mb-4">
          <p className="font-semibold">Selected Folder:</p>
          <p className="text-sm">{folderPath}</p>
        </div>
      )}

      {folderStats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-md shadow">
            <FileText className="text-blue-500 mb-2" />
            <p className="font-semibold">Total Images</p>
            <p className="text-2xl">{folderStats.total_images}</p>
          </div>
          <div className="bg-white p-4 rounded-md shadow">
            <Database className="text-green-500 mb-2" />
            <p className="font-semibold">Processed Images</p>
            <p className="text-2xl">{folderStats.processed_images}</p>
          </div>
        </div>
      )}

      {folderPath && (
        <button 
          onClick={processFolderImages}
          className="w-full bg-green-500 text-white py-3 rounded-md hover:bg-green-600 mt-4"
        >
          Process All Images
        </button>
      )}
    </div>
  );
};

export default FolderProcessor;