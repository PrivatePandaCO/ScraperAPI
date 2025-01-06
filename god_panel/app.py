# god_panel/app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
import os
from common.authentication import validate_uuid
from common.logging import setup_logging
from functools import wraps

# Setup logging
logger = setup_logging("god_panel")

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Change this to a secure key

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'god_panel_config.json')
with open(CONFIG_PATH) as f:
    config = json.load(f)

ADMIN_UUID = config['god_panel']['admin_uuid']
LICENSE_SERVER_URL = f"http://{config['license_server']['ip']}:{config['license_server']['port']}/"
PUBLIC_SERVER_URL = f"http://{config['public_server']['ip']}:{config['public_server']['port']}/"
SCRAPER_SERVERS = config['scraper_servers']

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({"error": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    uuid_input = request.form.get('uuid')
    if validate_uuid(uuid_input, ADMIN_UUID):
        session['logged_in'] = True
        logger.info("Admin logged in successfully")
        flash('Logged in successfully.', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid UUID. Access denied.', 'danger')
        logger.warning("Failed admin login attempt")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/licenses')
@login_required
def licenses():
    return render_template('licenses.html')

@app.route('/api/licenses', methods=['GET'])
@login_required
def api_list_licenses():
    try:
        response = requests.get(f"{LICENSE_SERVER_URL}list_licenses", timeout=5)
        licenses = response.json().get("licenses", [])
        return jsonify({"licenses": licenses})
    except requests.RequestException:
        logger.error("Failed to fetch licenses from License Server")
        return jsonify({"error": "Failed to fetch licenses"}), 500

@app.route('/api/create_license', methods=['POST'])
@login_required
def api_create_license():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    required_fields = {"key", "valid_until", "scrapers", "usage_per_month"}
    if not required_fields.issubset(data.keys()):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        response = requests.post(f"{LICENSE_SERVER_URL}create_license", json=data, timeout=5)
        if response.status_code == 200:
            logger.info(f"License {data['key']} created successfully")
            return jsonify({"status": "License created"}), 200
        else:
            error_detail = response.json().get('detail', 'Failed to create license.')
            logger.warning(f"License creation failed: {error_detail}")
            return jsonify({"error": error_detail}), response.status_code
    except requests.RequestException:
        logger.error("License server error during license creation")
        return jsonify({"error": "License server error"}), 500

@app.route('/api/delete_license', methods=['POST'])
@login_required
def api_delete_license():
    data = request.json
    if not data or 'key' not in data:
        return jsonify({"error": "License key is required"}), 400
    key = data['key']
    try:
        response = requests.post(f"{LICENSE_SERVER_URL}delete_license", json={"key": key}, timeout=5)
        if response.status_code == 200:
            logger.info(f"License {key} deleted successfully")
            return jsonify({"status": "License deleted"}), 200
        else:
            error_detail = response.json().get('detail', 'Failed to delete license.')
            logger.warning(f"License deletion failed: {error_detail}")
            return jsonify({"error": error_detail}), response.status_code
    except requests.RequestException:
        logger.error("License server error during license deletion")
        return jsonify({"error": "License server error"}), 500

@app.route('/server_loads')
@login_required
def server_loads():
    return render_template('server_loads.html')

@app.route('/api/server_loads', methods=['GET'])
@login_required
def api_server_loads():
    loads = {}
    for server in SCRAPER_SERVERS:
        try:
            response = requests.get(f"http://{server['ip']}:{server['port']}/load", timeout=5)
            if response.status_code == 200:
                loads[server['name']] = response.json().get("load", "Unknown")
            else:
                loads[server['name']] = "Error"
        except requests.RequestException:
            loads[server['name']] = "Unreachable"
    return jsonify({"server_loads": loads})

@app.route('/api/restart_services', methods=['POST'])
@login_required
def api_restart_services():
    # Implement service restart logic
    # For testing purposes, we'll simulate a restart
    # In production, consider using API endpoints or SSH commands to restart services
    # Example: Making HTTP requests to services to restart (if such endpoints exist)
    # Alternatively, use orchestration tools or service managers
    logger.info("Services restarted successfully")
    return jsonify({"status": "Services restarted"}), 200

if __name__ == '__main__':
    app.run(host=config['god_panel']['ip'], port=config['god_panel']['port'], debug=False, host='0.0.0.0')
