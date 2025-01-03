// src/components/CorrectionForm.js

import React, { useState } from 'react';

const CorrectionForm = ({ data, validationErrors, onSubmit }) => {
  const [correctedData, setCorrectedData] = useState(data);

  const handleChange = (field, value) => {
    setCorrectedData({ ...correctedData, [field]: value });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit(correctedData);
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-gray-100 rounded">
      <h2 className="text-xl font-semibold mb-4">Please correct the following fields:</h2>
      {Object.keys(validationErrors).map((field) => (
        <div key={field} className="mb-4">
          <label className="block mb-1">{field}:</label>
          <input
            type="text"
            value={correctedData[field] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            className="w-full p-2 border border-red-500 rounded"
          />
          <span className="text-red-500 text-sm">{validationErrors[field]}</span>
        </div>
      ))}
      <button type="submit" className="bg-green-500 text-white px-4 py-2 rounded">
        Submit Corrections
      </button>
    </form>
  );
};

export default CorrectionForm;