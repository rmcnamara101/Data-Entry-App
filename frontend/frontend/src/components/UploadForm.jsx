// src/components/UploadForm.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { Button, TextField, Typography, Paper } from '@mui/material';

function UploadForm() {
  const [file, setFile] = useState(null);
  const [response, setResponse] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!file) {
      alert('Please select a file.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    axios
      .post('http://localhost:5000/process-form', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      .then((res) => {
        setResponse(res.data);
        console.log(res.data);
      })
      .catch((err) => {
        console.error(err);
        alert('An error occurred while processing the form.');
      });
  };

  return (
    <Paper elevation={3} style={{ padding: '20px', marginTop: '20px' }}>
      <Typography variant="h5">Upload Patient Form</Typography>
      <form onSubmit={handleSubmit}>
        <div>
          <Button variant="contained" component="label">
            Select Form
            <input type="file" hidden onChange={handleFileChange} accept="image/*,.pdf" />
          </Button>
          {file && <Typography variant="body1">{file.name}</Typography>}
        </div>
        <Button type="submit" variant="contained" color="primary" style={{ marginTop: '10px' }}>
          Upload and Process
        </Button>
      </form>
      {response && (
        <div style={{ marginTop: '20px' }}>
          <Typography variant="h6">Processing Result:</Typography>
          <pre>{JSON.stringify(response.data, null, 2)}</pre>
        </div>
      )}
    </Paper>
  );
}


export default UploadForm;