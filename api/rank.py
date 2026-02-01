import json
import os
from http.server import BaseHTTPRequestHandler
from multipart.multipart import FormParser

from warm_ranker import main  # Import your main function

class handler(BaseHTTPRequestHandler):
  def do_POST(self):
    csv_path = None
    try:
      # Check Content-Length header
      if 'Content-Length' not in self.headers:
        self.send_response(411)  # Length Required
        self.end_headers()
        self.wfile.write(b'{"error": "Content-Length header required"}')
        return
      
      try:
        content_length = int(self.headers['Content-Length'])
      except (ValueError, TypeError):
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"error": "Invalid Content-Length"}')
        return
      
      if content_length <= 0:
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"error": "Content-Length must be positive"}')
        return
      
      post_data = self.rfile.read(content_length)
      content_type = self.headers.get('Content-Type', '')
      
      if not content_type or 'multipart/form-data' not in content_type:
        self.send_response(400)
        self.end_headers()
        self.wfile.write(b'{"error": "Content-Type must be multipart/form-data"}')
        return
      
      # Parse multipart form data using callbacks
      fields = {}
      files = {}
      
      def on_field(field):
        try:
          fields[field.field_name.decode()] = field.value.decode()
        except (AttributeError, UnicodeDecodeError):
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

      # Safe file path handling
      file_name = csv_file.file_name.decode() if csv_file.file_name else 'upload.csv'
      # Sanitize filename
      file_name = os.path.basename(file_name).replace('..', '').replace('/', '').replace('\\', '')
      csv_path = os.path.join('/tmp', file_name)
      
      # Write file
      try:
        with open(csv_path, 'wb') as f:
          file_data = csv_file.value if hasattr(csv_file, 'value') else csv_file.file.read() if hasattr(csv_file, 'file') else b''
          f.write(file_data)
      except Exception as e:
        self.send_response(500)
        self.end_headers()
        self.wfile.write(json.dumps({'error': f'Failed to save file: {str(e)}'}).encode())
        return

      # Process request
      ranked = main(idea, csv_path)  # Your main returns dict of records
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps(ranked).encode())
      
    except Exception as e:
      self.send_response(500)
      self.end_headers()
      self.wfile.write(json.dumps({'error': str(e)}).encode())
    finally:
      # Safe cleanup
      if csv_path and os.path.exists(csv_path):
        try:
          os.unlink(csv_path)
        except Exception:
          pass  # Ignore cleanup errors