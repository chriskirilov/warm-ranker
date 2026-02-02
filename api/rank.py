import json
import os
import sys
import logging
from http.server import BaseHTTPRequestHandler

logging.basicConfig(level=logging.ERROR)

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
            MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB total limit
            MAX_BUFFER_SIZE = 4294967296  # Node.js max (4GB)
            
            # CRITICAL: Validate Content-Length immediately to prevent Vercel wrapper buffer overflow
            # This must happen before reading any data
            if 'Content-Length' in self.headers:
                try:
                    content_length = int(self.headers['Content-Length'])
                    # Reject invalid sizes immediately
                    if content_length < 0:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'{"error": "Invalid Content-Length: negative value"}')
                        return
                    if content_length > MAX_BUFFER_SIZE:
                        self.send_response(413)
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': f'Content-Length exceeds buffer limit ({MAX_BUFFER_SIZE} bytes)'}).encode())
                        return
                    if content_length > MAX_TOTAL_SIZE:
                        self.send_response(413)
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': f'File too large (max {MAX_TOTAL_SIZE} bytes)'}).encode())
                        return
                except (ValueError, TypeError, OverflowError):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"error": "Invalid Content-Length header"}')
                    return
            
            # Now safe to read - use chunked reading
            MAX_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
            content_length = int(self.headers.get('Content-Length', 0)) if 'Content-Length' in self.headers else 0
            
            # Read body in chunks
            post_data = b''
            if content_length > 0:
                remaining = min(content_length, MAX_TOTAL_SIZE)
                while remaining > 0:
                    chunk_size = min(MAX_CHUNK_SIZE, remaining)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    post_data += chunk
                    remaining -= len(chunk)
            else:
                # No Content-Length, read available data
                post_data = self.rfile.read(MAX_TOTAL_SIZE)
            
            if len(post_data) == 0:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"status": "ok", "message": "Ready"}')
                return
            
            # Parse multipart form data
            from multipart.multipart import FormParser
            
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Content-Type must be multipart/form-data"}')
                return
            
            fields = {}
            files = {}
            
            def on_field(field):
                try:
                    fields[field.field_name.decode()] = field.value.decode()
                except:
                    pass
            
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
            
            # Save file
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
            
            # Process
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
                except:
                    pass
