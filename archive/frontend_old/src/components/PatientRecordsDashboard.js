import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Download, 
  RefreshCw, 
  Search,
  SortAsc,
  SortDesc,
  FileText
} from 'lucide-react';

const PatientRecordsDashboard = () => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [stats, setStats] = useState({
    totalRecords: 0,
    averageConfidence: 0
  });

  // Sample data for initial development - remove this when connecting to real API
  const sampleRecords = [
    {
      id: 1,
      patient_id: 'P001',
      patient_name: 'John Doe',
      scan_date: '2024-03-15',
      ocr_confidence: 95,
      file_path: '/scans/P001/scan1.pdf'
    },
    {
      id: 2,
      patient_id: 'P002',
      patient_name: 'Jane Smith',
      scan_date: '2024-03-16',
      ocr_confidence: 88,
      file_path: '/scans/P002/scan1.pdf'
    }
  ];

  useEffect(() => {
    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/records');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      setRecords(data);
      setStats({
        totalRecords: data.length,
        averageConfidence: data.reduce((acc, curr) => acc + (curr.ocr_confidence || 0), 0) / data.length
      });
    } catch (error) {
      console.error('Error fetching records:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const csvContent = filteredRecords.map(record => 
        Object.values(record).join(',')
      ).join('\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `patient-records-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting records:', error);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return null;
    }
    return sortConfig.direction === 'asc' ? 
      <SortAsc className="h-4 w-4" /> : 
      <SortDesc className="h-4 w-4" />;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const filteredRecords = React.useMemo(() => {
    let filtered = [...records];
    
    if (searchTerm) {
      filtered = filtered.filter(record => 
        record.patient_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        record.patient_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        record.file_path.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    if (sortConfig.key) {
      filtered.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    
    return filtered;
  }, [records, searchTerm, sortConfig]);

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Total Records</p>
              <p className="text-2xl font-bold">{stats.totalRecords}</p>
            </div>
            <Users className="h-8 w-8 text-blue-500" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Avg. Confidence</p>
              <p className="text-2xl font-bold">{stats.averageConfidence.toFixed(1)}%</p>
            </div>
            <FileText className="h-8 w-8 text-green-500" />
          </div>
        </div>
      </div>

      {/* Main Records Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Patient Records</h2>
            <div className="flex space-x-2">
              <button
                onClick={fetchRecords}
                className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </button>
              <button
                onClick={handleExport}
                className="flex items-center px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors"
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </button>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-center space-x-2">
              <Search className="h-4 w-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search records..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full max-w-sm px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th 
                  onClick={() => handleSort('patient_id')}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                >
                  <div className="flex items-center space-x-1">
                    <span>Patient ID</span>
                    {getSortIcon('patient_id')}
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('patient_name')}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                >
                  <div className="flex items-center space-x-1">
                    <span>Patient Name</span>
                    {getSortIcon('patient_name')}
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('scan_date')}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                >
                  <div className="flex items-center space-x-1">
                    <span>Scan Date</span>
                    {getSortIcon('scan_date')}
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('ocr_confidence')}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer"
                >
                  <div className="flex items-center space-x-1">
                    <span>OCR Confidence</span>
                    {getSortIcon('ocr_confidence')}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File Path
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="5" className="text-center py-4">Loading...</td>
                </tr>
              ) : filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-4">No records found</td>
                </tr>
              ) : (
                filteredRecords.map((record) => (
                  <tr key={record.id}>
                    <td className="px-6 py-4 whitespace-nowrap">{record.patient_id}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{record.patient_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{formatDate(record.scan_date)}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                          <div 
                            className="bg-blue-500 rounded-full h-2"
                            style={{ width: `${record.ocr_confidence}%` }}
                          />
                        </div>
                        <span>{record.ocr_confidence}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 truncate max-w-xs">{record.file_path}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PatientRecordsDashboard;