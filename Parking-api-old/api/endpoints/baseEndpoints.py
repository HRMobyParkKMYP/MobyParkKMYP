class BaseEndpoint:
    def setup(self, request_handler):
        return (
            request_handler.path,
            request_handler.send_response,
            request_handler.send_header,
            request_handler.end_headers,
            request_handler.wfile
        )