import React from 'react';

const Dashboard = () => (
  <div className="bg-gray-100 p-8 rounded-lg">
    <h2 className="text-3xl font-bold mb-6">Dashboard</h2>
    <div className="grid grid-cols-3 gap-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-xl font-semibold mb-4">Processed Forms</h3>
        <p className="text-4xl font-bold text-blue-600">124</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-xl font-semibold mb-4">Pending Scans</h3>
        <p className="text-4xl font-bold text-yellow-600">12</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-xl font-semibold mb-4">Database Entries</h3>
        <p className="text-4xl font-bold text-green-600">356</p>
      </div>
    </div>
  </div>
);

export default Dashboard;