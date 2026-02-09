from flask import Flask, render_template, request, jsonify, send_file
import os
import yt_dlp
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'v2-converter-secret'

# Folders
DOWNLOAD_FOLDER = 'downloads'
COOKIES_FILE = 'cookies.txt'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url')
    format_type = request.form.get('format', 'mp3')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Configure yt-dlp with cookies
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
        }

        # Add cookies if file exists
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        if format_type == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:  # mp4
            ydl_opts.update({
                'format': 'best[ext=mp4]/best',
            })

        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_type == 'mp3':
                filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')

            # Get the actual filename
            base_name = os.path.basename(filename)

            return jsonify({
                'success': True,
                'filename': base_name,
                'title': info.get('title', 'Download'),
                'duration': info.get('duration_string', 'Unknown')
            })

    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            error_msg = "YouTube requires cookies. Please upload fresh cookies.txt"
        return jsonify({'error': error_msg}), 500

@app.route('/download/<filename>')
def download(filename):
    try:
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-cookies')
def check_cookies():
    """Check if cookies file exists"""
    exists = os.path.exists(COOKIES_FILE)
    return jsonify({'cookies_exists': exists})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
