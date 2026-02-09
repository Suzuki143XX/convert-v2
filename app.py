from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import yt_dlp
import glob
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'v2-converter-secret'

# Folders
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.txt')

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_ydl_opts(format_type):
    """Get yt-dlp options"""
    opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    # Add cookies if exists
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE

    if format_type == 'mp3':
        opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:  # mp4
        opts.update({
            'format': 'best[ext=mp4]/best',
        })

    return opts

def find_downloaded_file(base_name, format_type):
    """Find the actual downloaded file"""
    # Look for files with similar name
    pattern = os.path.join(DOWNLOAD_FOLDER, f"*{base_name}*")
    files = glob.glob(pattern)

    if format_type == 'mp3':
        # Prefer mp3 files
        mp3_files = [f for f in files if f.endswith('.mp3')]
        if mp3_files:
            return mp3_files[0]
    else:
        # Prefer mp4 files
        mp4_files = [f for f in files if f.endswith('.mp4')]
        if mp4_files:
            return mp4_files[0]

    # Return any file if specific type not found
    if files:
        return files[0]

    return None

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
        # Clean old files (keep only last 10)
        files = sorted(glob.glob(os.path.join(DOWNLOAD_FOLDER, '*')), key=os.path.getctime)
        if len(files) > 10:
            for f in files[:-10]:
                try:
                    os.remove(f)
                except:
                    pass

        ydl_opts = get_ydl_opts(format_type)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Get the expected filename
            if format_type == 'mp3':
                expected_ext = 'mp3'
            else:
                expected_ext = 'mp4'

            # Find the actual file
            title = info.get('title', 'download')
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in ' -_.']).rstrip()

            # Look for the file
            downloaded_file = None
            files_in_dir = os.listdir(DOWNLOAD_FOLDER)

            # Find newest file (the one we just downloaded)
            files_with_time = [(f, os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f))) for f in files_in_dir]
            files_with_time.sort(key=lambda x: x[1], reverse=True)

            for f, _ in files_with_time:
                if f.endswith(f'.{expected_ext}'):
                    downloaded_file = f
                    break

            if not downloaded_file and files_with_time:
                # Take newest file regardless of extension
                downloaded_file = files_with_time[0][0]

            if not downloaded_file:
                return jsonify({'error': 'File not found after download'}), 500

            return jsonify({
                'success': True,
                'filename': downloaded_file,
                'title': title,
                'format': format_type
            })

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        if "Sign in to confirm" in error_msg:
            error_msg = "YouTube requires fresh cookies. Please update cookies.txt"
        return jsonify({'error': error_msg}), 500

@app.route('/download/<path:filename>')
def download(filename):
    """Serve file with proper headers for download"""
    try:
        # Security: prevent directory traversal
        filename = os.path.basename(filename)
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)

        print(f"Download requested: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")

        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Determine MIME type
        if filename.endswith('.mp3'):
            mimetype = 'audio/mpeg'
            download_name = filename
        elif filename.endswith('.mp4'):
            mimetype = 'video/mp4'
            download_name = filename
        else:
            mimetype = 'application/octet-stream'
            download_name = filename

        # Serve file with download headers
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-cookies')
def check_cookies():
    exists = os.path.exists(COOKIES_FILE)
    return jsonify({'cookies_exists': exists})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
