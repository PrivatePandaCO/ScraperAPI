// god_panel/static/js/scripts.js

document.addEventListener('DOMContentLoaded', function() {
    // License Management
    const licensesTableBody = document.getElementById('licenses-table-body');
    const addLicenseBtn = document.getElementById('add-license-btn');
    const addLicenseModal = document.getElementById('add-license-modal');
    const closeModalSpan = document.querySelector('.close');
    const addLicenseForm = document.getElementById('add-license-form');

    // Fetch and display licenses
    function fetchLicenses() {
        fetch('/api/licenses')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }
                licensesTableBody.innerHTML = '';
                data.licenses.forEach(license => {
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>${license.key}</td>
                        <td>${license.valid_until}</td>
                        <td>${license.scrapers.join(', ')}</td>
                        <td>${license.usage_per_month}</td>
                        <td>${license.usage_count}</td>
                        <td>
                            <button class="delete-license-btn" data-key="${license.key}">Delete</button>
                        </td>
                    `;
                    licensesTableBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching licenses:', error);
            });
    }

    fetchLicenses();

    // Open Add License Modal
    addLicenseBtn.addEventListener('click', function() {
        addLicenseModal.style.display = 'block';
    });

    // Close Modal
    closeModalSpan.addEventListener('click', function() {
        addLicenseModal.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target == addLicenseModal) {
            addLicenseModal.style.display = 'none';
        }
    });

    // Handle Add License Form Submission
    addLicenseForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const key = document.getElementById('key').value;
        const valid_until = document.getElementById('valid_until').value;
        const scrapersSelect = document.getElementById('scrapers');
        const selectedScrapers = Array.from(scrapersSelect.selectedOptions).map(option => option.value);
        const usage_per_month = document.getElementById('usage_per_month').value;

        const payload = {
            key,
            valid_until,
            scrapers: selectedScrapers,
            usage_per_month: parseInt(usage_per_month)
        };

        fetch('/api/create_license', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(result => {
            if (result.status === 200) {
                alert('License created successfully.');
                addLicenseModal.style.display = 'none';
                addLicenseForm.reset();
                fetchLicenses();
            } else {
                alert(`Error: ${result.body.error}`);
            }
        })
        .catch(error => {
            console.error('Error creating license:', error);
            alert('Failed to create license.');
        });
    });

    // Handle Delete License
    licensesTableBody.addEventListener('click', function(event) {
        if (event.target && event.target.matches('button.delete-license-btn')) {
            const key = event.target.getAttribute('data-key');
            if (confirm(`Are you sure you want to delete license ${key}?`)) {
                fetch('/api/delete_license', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ key })
                })
                .then(response => response.json().then(data => ({ status: response.status, body: data })))
                .then(result => {
                    if (result.status === 200) {
                        alert('License deleted successfully.');
                        fetchLicenses();
                    } else {
                        alert(`Error: ${result.body.error}`);
                    }
                })
                .catch(error => {
                    console.error('Error deleting license:', error);
                    alert('Failed to delete license.');
                });
            }
        }
    });

    // Server Loads
    const serverLoadsTableBody = document.getElementById('server-loads-table-body');

    function fetchServerLoads() {
        fetch('/api/server_loads')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }
                serverLoadsTableBody.innerHTML = '';
                for (const [name, load] of Object.entries(data.server_loads)) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${name}</td>
                        <td>${load}</td>
                    `;
                    serverLoadsTableBody.appendChild(row);
                }
            })
            .catch(error => {
                console.error('Error fetching server loads:', error);
            });
    }

    // Fetch server loads on page load
    if (serverLoadsTableBody) {
        fetchServerLoads();
    }

    // Restart Services
    const restartServicesBtn = document.getElementById('restart-services-btn');
    if (restartServicesBtn) {
        restartServicesBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to restart all services?')) {
                fetch('/api/restart_services', {
                    method: 'POST'
                })
                .then(response => response.json().then(data => ({ status: response.status, body: data })))
                .then(result => {
                    if (result.status === 200) {
                        alert('Services restarted successfully.');
                    } else {
                        alert(`Error: ${result.body.error}`);
                    }
                })
                .catch(error => {
                    console.error('Error restarting services:', error);
                    alert('Failed to restart services.');
                });
            }
        });
    }
});
