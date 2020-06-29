from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading
import logging


class Router(BaseHTTPRequestHandler):
    """
    a simple http catch-all for doing k8s healthchecks in support
    of the statefulset, which requires a service endpoint. Use
    self.path here to define routes.
    """

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes("OK", "utf-8"))
        self.wfile.write(bytes("\n", "utf-8"))
        return


class ServiceEndpoint(threading.Thread):
    def __init__(self, host="127.0.0.1", port=8080):
        # note the port you use here should match what you define
        # in your service manifest
        super().__init__()
        self._shutdown = False
        self.server = ThreadingHTTPServer((host, port), Router)

    @property
    def shutdown(self):
        return self._shutdown

    def terminate(self):
        logging.info(f"Stopping Service endpoint")
        self._shutdown = True
        self.server.server_close()

    def run(self):
        try:
            self.server.serve_forever()
            logging.info("Service endpoint running")
        except:
            pass
        self.terminate()
