import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
  def log_message(self, format, *args):
    pass  # Suppress logging
  
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'status': 'ok'}).encode())
  
  def do_POST(self):
    # Immediately read any body data to prevent Node.js wrapper buffer issues
    try:
      content_length = self.headers.get('Content-Length', '0')
      try:
        cl = int(content_length)
        # Only read if reasonable size (max 10MB)
        if 0 < cl <= 10 * 1024 * 1024:
          _ = self.rfile.read(cl)
      except (ValueError, OverflowError):
        # Invalid Content-Length - just continue
        pass
    except:
      pass
    
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'status': 'ok'}).encode())
