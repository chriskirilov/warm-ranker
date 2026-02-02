import json
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'status': 'ok', 'message': 'GET handler working'}).encode())
  
  def do_POST(self):
    try:
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'status': 'ok', 'message': 'POST handler working'}).encode())
    except Exception as e:
      self.send_response(500)
      self.send_header('Content-type', 'application/json')
      self.end_headers()
      self.wfile.write(json.dumps({'error': str(e)}).encode())
