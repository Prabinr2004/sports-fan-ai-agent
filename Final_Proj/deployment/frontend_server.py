"""
Simple Flask server to serve the frontend static files on Render
"""
import os
from flask import Flask, render_template_string, send_from_directory

app = Flask(__name__, static_folder='frontend/static', static_url_path='/static')

@app.route('/')
def index():
    """Serve the main index.html"""
    with open(os.path.join('frontend', 'index.html'), 'r') as f:
        return f.read()

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('frontend/static', path)

@app.errorhandler(404)
def not_found(error):
    """Serve index.html for all other routes (SPA routing)"""
    with open(os.path.join('frontend', 'index.html'), 'r') as f:
        return f.read()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
