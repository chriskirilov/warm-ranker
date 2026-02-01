import json
import os
from http.server import BaseHTTPRequestHandler
from multipart import parse_form  # For form parsing (add to requirements.txt: pip install multipart)

from warm_ranker import main  # Import your main function

class handler(BaseHTTPRequestHandler):
  def do_POST(self):
    content_length = int(self.headers['Content-Length'])
    post_data = self.rfile.read(content_length)
    form = parse_form(post_data, self.headers['Content-Type'], self.headers.get('Content-Length'))
    idea = form.get('idea')[0] if 'idea' in form else ''
    csv = form.get('csv') if 'csv' in form else None

    if not idea or not csv:
      self.send_response(400)
      self.end_headers()
      self.wfile.write(b'{"error": "Missing idea or CSV"}')
      return

    csv_path = os.path.join('/tmp', csv.filename)
    with open(csv_path, 'wb') as f:
      f.write(csv.content)

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