// src/components/DatabaseManagement.js

import React, { useState, useEffect } from 'react';

const DatabaseManagement = () => {
  const [patientRecords, setPatientRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPatientRecords();
  }, []);

  const fetchPatientRecords = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/patient-records');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setPatientRecords(data.records);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching patient records:', error);
      setError(error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-gray-500 text-lg">Loading patient records...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-red-500 text-lg">
          Error fetching patient records: {error.message}
        </div>
      </div>
    );
  }

  const totalForms = patientRecords.length;

  return (
    <div className="p-8">
      <h2 className="text-3xl font-bold mb-6 text-gray-800">Patient Records</h2>
      
      {/* Database Information Card */}
      <div className="mb-8">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex flex-col sm:flex-row sm:justify-between">
            <div>
              <p className="text-gray-600">Total Loaded Forms</p>
              <p className="text-2xl font-semibold text-gray-800">{totalForms}</p>
            </div>
            {/* You can add more statistics here if needed */}
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="bg-white shadow rounded-lg overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Request Number
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Name
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Date of Birth
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                OCR Confidence
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {patientRecords.length > 0 ? (
              patientRecords.map((record) => (
                <tr key={record.id} className="hover:bg-gray-100 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {record.request_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {record.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {record.date_of_birth
                      ? new Date(record.date_of_birth).toLocaleDateString()
                      : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                    {record.ocr_confidence !== null
                      ? record.ocr_confidence.toFixed(2)
                      : 'N/A'}
                  </td>
                </tr>
              ))
            ) : (
              // Display a message or empty rows when there are no records
              <tr>
                <td
                  className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500"
                  colSpan="4"
                >
                  No patient records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DatabaseManagement;