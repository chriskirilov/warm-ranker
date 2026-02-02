import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
  def _read_body(self):
    """Safely read request body with size limits"""
    try:
      content_length = self.headers.get('Content-Length')
      if content_length:
        try:
          length = int(content_length)
          # Limit to 10MB to prevent buffer overflow
          if length > 10 * 1024 * 1024:
            return None
          if length > 0:
            return self.rfile.read(length)
        except (ValueError, OverflowError):
          return None
      return None
    except Exception:
      return None
  
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'status': 'ok', 'message': 'GET handler working'}).encode())
  
  def do_POST(self):
    try:
      # Read and discard body to prevent buffer overflow in Node.js wrapper
      body = self._read_body()
      
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'status': 'ok', 'message': 'POST handler working'}).encode())
    except Exception as e:
      self.send_response(500)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'error': str(e)}).encode())
