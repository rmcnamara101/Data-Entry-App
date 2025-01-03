// src/components/FormUpload.js

import React, { useState } from 'react';
import CorrectionForm from './CorrectionForm';

const FormUpload = () => {
  const [file, setFile] = useState(null);
  const [extractedData, setExtractedData] = useState({});
  const [validationErrors, setValidationErrors] = useState({});
  const [showCorrectionForm, setShowCorrectionForm] = useState(false);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();

    if (!file) {
      alert('Please select a file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/process-form', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.status === 200) {
        // Form processed successfully
        setExtractedData(result.data);
        alert('Form processed successfully!');
        // Proceed with displaying or using the extracted data
      } else if (response.status === 400) {
        // Validation errors occurred
        setExtractedData(result.data);
        setValidationErrors(result.validation_errors);
        setShowCorrectionForm(true);
      } else {
        // Handle other errors
        console.error('Error:', result.error);
        alert('An error occurred while processing the form.');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while connecting to the server.');
    }
  };

  const handleCorrectionsSubmit = async (correctedData) => {
    try {
      const response = await fetch('http://localhost:5000/submit-corrections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(correctedData),
      });

      const result = await response.json();

      if (response.status === 200) {
        // Corrections submitted successfully
        alert('Corrections submitted successfully.');
        setShowCorrectionForm(false);
        // Optionally, proceed with the next steps
      } else {
        // Handle errors
        console.error('Error:', result.error);
        alert('An error occurred while submitting corrections.');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while connecting to the server.');
    }
  };

  return (
    <div className="p-8">
      {!showCorrectionForm ? (
        <form onSubmit={handleFormSubmit}>
          <label className="block mb-2">
            Upload Form Image:
            <input type="file" accept="image/*" onChange={handleFileChange} className="mt-1" />
          </label>
          <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded">
            Submit
          </button>
        </form>
      ) : (
        <CorrectionForm
          data={extractedData}
          validationErrors={validationErrors}
          onSubmit={handleCorrectionsSubmit}
        />
      )}
    </div>
  );
};

export default FormUpload;