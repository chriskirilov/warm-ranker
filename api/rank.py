import json
import os
from http.server import BaseHTTPRequestHandler
from multipart.multipart import FormParser

from warm_ranker import main  # Import your main function

class handler(BaseHTTPRequestHandler):
  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    post_data = self.rfile.read(content_length)
    content_type = self.headers.get('Content-Type', '')
    
    # Parse multipart form data using callbacks
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

    csv_path = os.path.join('/tmp', csv_file.file_name.decode() if csv_file.file_name else 'upload.csv')
    with open(csv_path, 'wb') as f:
      f.write(csv_file.value)

    try:
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
      os.unlink(csv_path)  # Cleanup