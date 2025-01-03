// SettingsPage.jsx

import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SettingsPage = () => {
    const [defaultFolder, setDefaultFolder] = useState('');
    const [message, setMessage] = useState('');

    useEffect(() => {
        axios.get('/api/default-folder')
            .then(response => {
                setDefaultFolder(response.data.default_folder);
            })
            .catch(error => {
                console.error('Error fetching default folder:', error);
            });
    }, []);

    const handleUpdateFolder = (e) => {
        e.preventDefault();
        axios.post('/api/set-default-folder', { default_folder: defaultFolder })
            .then(response => {
                if (response.data.success) {
                    setMessage('Default scan folder updated successfully.');
                } else {
                    setMessage('Failed to update default scan folder.');
                }
            })
            .catch(error => {
                console.error('Error updating default scan folder:', error);
                setMessage('An error occurred while updating the default scan folder.');
            });
    };

    const handleClearDatabase = () => {
        const confirmClear = window.confirm("Are you sure you want to clear the database? This action cannot be undone.");
        if (confirmClear) {
            axios.post('/api/clear-database')
                .then(response => {
                    if (response.status === 200 && response.data.success) {
                        setMessage(`Database cleared successfully. ${response.data.deleted_records} records deleted.`);
                    } else {
                        setMessage('Failed to clear the database.');
                    }
                })
                .catch(error => {
                    console.error('Error clearing database:', error);
                    setMessage('An error occurred while clearing the database.');
                });
        }
    };

    return (
        <div>
            <h2>Settings</h2>
            <form onSubmit={handleUpdateFolder}>
                <label>
                    Default Scan Folder:
                    <input
                        type="text"
                        value={defaultFolder}
                        onChange={(e) => setDefaultFolder(e.target.value)}
                        required
                    />
                </label>
                <button type="submit">Update</button>
            </form>
            <button onClick={handleClearDatabase} style={{ marginTop: '20px', backgroundColor: 'red', color: 'white' }}>
                Clear Database
            </button>
            {message && <p>{message}</p>}
        </div>
    );
};

export default SettingsPage;