import http.server
import socketserver
from http.server import SimpleHTTPRequestHandler
import os

# Create a custom handler to enable threading (though socketserver.ThreadingTCPServer does the threading)
class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable caching instructions for images
        if self.path.endswith(('.jpg', '.png', '.jpeg', '.gif')):
            self.send_header('Cache-Control', 'public, max-age=31536000') # Cache for 1 year
        else:
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

PORT = 8081
DIRECTORY = "src/web/frontend/"

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with ThreadingHTTPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT} with threading enabled")
        httpd.serve_forever()
