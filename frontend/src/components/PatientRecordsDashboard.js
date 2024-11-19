import React, { useState, useEffect } from 'react';
import { Table } from '../ui/table';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { Input } from '../ui/input';
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

  useEffect(() => {
    fetchRecords();
  }, []);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/patient-records');
      const data = await response.json();
      setRecords(data.records);
      setStats({
        totalRecords: data.records.length,
        averageConfidence: calculateAverageConfidence(data.records)
      });
    } catch (error) {
      console.error('Error fetching records:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateAverageConfidence = (records) => {
    const confidenceScores = records
      .filter(record => record.ocr_confidence != null)
      .map(record => record.ocr_confidence);
    return confidenceScores.length > 0 
      ? (confidenceScores.reduce((a, b) => a + b) / confidenceScores.length).toFixed(2)
      : 0;
  };

  const handleExport = async () => {
    try {
      const response = await fetch('/api/export-records');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'patient_records.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const sortedRecords = React.useMemo(() => {
    if (!sortConfig.key) return records;

    return [...records].sort((a, b) => {
      if (sortConfig.key === 'scan_date') {
        return sortConfig.direction === 'asc' 
          ? new Date(a[sortConfig.key]) - new Date(b[sortConfig.key])
          : new Date(b[sortConfig.key]) - new Date(a[sortConfig.key]);
      }

      if (a[sortConfig.key] < b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (a[sortConfig.key] > b[sortConfig.key]) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [records, sortConfig]);

  const filteredRecords = sortedRecords.filter(record =>
    Object.values(record).some(value =>
      value?.toString().toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const getSortIcon = (key) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />;
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Total Records</p>
                <p className="text-2xl font-bold">{stats.totalRecords}</p>
              </div>
              <Users className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Avg. Confidence</p>
                <p className="text-2xl font-bold">{stats.averageConfidence}%</p>
              </div>
              <FileText className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Records Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-2xl font-bold">Patient Records</CardTitle>
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
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="flex items-center space-x-2">
              <Search className="h-4 w-4 text-gray-500" />
              <Input
                placeholder="Search records..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="max-w-sm"
              />
            </div>
          </div>
          
          <div className="rounded-md border">
            <Table>
              <thead>
                <tr>
                  <th 
                    onClick={() => handleSort('patient_id')}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Patient ID</span>
                      {getSortIcon('patient_id')}
                    </div>
                  </th>
                  <th 
                    onClick={() => handleSort('patient_name')}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Patient Name</span>
                      {getSortIcon('patient_name')}
                    </div>
                  </th>
                  <th 
                    onClick={() => handleSort('scan_date')}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Scan Date</span>
                      {getSortIcon('scan_date')}
                    </div>
                  </th>
                  <th 
                    onClick={() => handleSort('ocr_confidence')}
                    className="cursor-pointer"
                  >
                    <div className="flex items-center space-x-1">
                      <span>OCR Confidence</span>
                      {getSortIcon('ocr_confidence')}
                    </div>
                  </th>
                  <th>File Path</th>
                </tr>
              </thead>
              <tbody>
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
                      <td>{record.patient_id}</td>
                      <td>{record.patient_name}</td>
                      <td>{formatDate(record.scan_date)}</td>
                      <td>
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
                      <td className="truncate max-w-xs">{record.file_path}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PatientRecordsDashboard;