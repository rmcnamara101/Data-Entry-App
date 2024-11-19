import React from 'react';

const Settings = () => (
  <div className="bg-white p-8 rounded-lg">
    <h2 className="text-2xl font-bold mb-6">Application Settings</h2>
    <div className="space-y-4">
      <div>
        <label className="block mb-2">Default Scan Directory</label>
        <input
          type="text"
          placeholder="/path/to/default/directory"
          className="w-full px-3 py-2 border rounded"
        />
      </div>
      <div>
        <label className="block mb-2">OCR Confidence Threshold</label>
        <input type="range" min="0" max="100" className="w-full" />
      </div>
    </div>
  </div>
);

export default Settings;