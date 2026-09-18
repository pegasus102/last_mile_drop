import http.server
import socketserver
import json
import os
import sys

# Ensure LocalStack targets are set
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_ENDPOINT_URL"] = "http://localhost:4566"
os.environ["TABLE_NAME"] = "Deliveries"

sys.path.insert(0, '.aws-sam/build/WhisperProcessor')
from index import lambda_handler

class LocalAPIHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            # Read the incoming JSON payload from frontend
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))

            # Pass to the Lambda handler
            event = {"body": json.dumps(payload)}
            result = lambda_handler(event, None)

            # Send back the response
            self.send_response(result.get('statusCode', 200))
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(result['body'].encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            print(f"Server Error: {e}")

PORT = 8080
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), LocalAPIHandler) as httpd:
    print(f"🚀 Serving UI and API Bridge on http://localhost:{PORT}")
    httpd.serve_forever()
