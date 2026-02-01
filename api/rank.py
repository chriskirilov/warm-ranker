import json
import os
import sys
import logging
from http.server import BaseHTTPRequestHandler
from multipart.multipart import FormParser

logging.basicConfig(level=logging.ERROR)  # For Vercel logs

# Lazy import
_main_func = None

def get_main():
    global _main_func
    if _main_func is None:
        try:
            from warm_ranker import main
            _main_func = main
        except Exception as e:
            logging.error(f"Error importing warm_ranker: {e}")
            raise
    return _main_func

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "message": "Warm Ranker API"}')
        except Exception as e:
            try:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            except:
                pass

    def do_POST(self):
        csv_path = None
        try:
            MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit

            # Handle Content-Length
            if 'Content-Length' not in self.headers:
                post_data = self.rfile.read(MAX_CONTENT_LENGTH)
                content_length = len(post_data)
            else:
                content_length = int(self.headers['Content-Length'])

            if content_length > MAX_CONTENT_LENGTH:
                self.send_response(413)
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'File too large (max {MAX_CONTENT_LENGTH} bytes)'}).encode())
                return

            post_data = self.rfile.read(content_length)

            if len(post_data) == 0:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "ok", "message": "Ready to process requests"}')
                return

            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Content-Type must be multipart/form-data"}')
                return

            # Parse form
            fields = {}
            files = {}

            def on_field(field):
                fields[field.field_name.decode()] = field.value.decode()

            def on_file(file):
                files[file.field_name.decode()] = file

            parser = FormParser(content_type, on_field=on_field, on_file=on_file)
            parser.write(post_data)
            parser.finalize()

            idea = fields.get('idea', '')
            csv_file = files.get('csv')

            if not idea or not csv_file:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Missing idea or CSV"}')
                return

            # Safe file handling
            file_name = csv_file.file_name.decode() if csv_file.file_name else 'upload.csv'
            file_name = os.path.basename(file_name).replace('..', '').replace('/', '').replace('\\', '')
            csv_path = os.path.join('/tmp', file_name)

            try:
                file_data = csv_file.value if hasattr(csv_file, 'value') else csv_file.file.read() if hasattr(csv_file, 'file') else b''
                with open(csv_path, 'wb') as f:
                    f.write(file_data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Failed to save file: {str(e)}'}).encode())
                return

            main = get_main()
            ranked = main(idea, csv_path)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(ranked).encode())

        except Exception as e:
            logging.error(str(e))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        finally:
            if csv_path and os.path.exists(csv_path):
                try:
                    os.unlink(csv_path)
                except Exception:
                    pass