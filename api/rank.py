import json
import sys
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
  def log_message(self, format, *args):
    # Suppress default logging
    pass
  
  def _validate_content_length(self):
    """Validate Content-Length header to prevent buffer overflow"""
    try:
      content_length = self.headers.get('Content-Length')
      if content_length:
        try:
          length = int(content_length)
          # Reject invalid Content-Length values
          if length < 0 or length > 10 * 1024 * 1024:  # 10MB max
            return False
        except (ValueError, OverflowError):
          return False
      return True
    except Exception:
      return False
  
  def do_GET(self):
    try:
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'status': 'ok', 'message': 'GET handler working'}).encode())
    except Exception as e:
      try:
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': str(e)}).encode())
      except:
        pass
  
  def do_POST(self):
    try:
      # Validate Content-Length before processing
      if not self._validate_content_length():
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Invalid Content-Length'}).encode())
        return
      
      # Read body if present (with limit)
      content_length = self.headers.get('Content-Length')
      if content_length:
        try:
          length = int(content_length)
          if 0 < length <= 10 * 1024 * 1024:
            body = self.rfile.read(length)
        except (ValueError, OverflowError):
          pass
      
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'status': 'ok', 'message': 'POST handler working'}).encode())
    except Exception as e:
      try:
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': str(e)}).encode())
      except:
        pass
