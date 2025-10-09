from http.server import HTTPServer, BaseHTTPRequestHandler
from endpoints.account import AccountHandler
from endpoints.profile import ProfileHandler
from endpoints.parking_lots import ParkingLotHandler
from endpoints.vehicles import VehicleHandler
from endpoints.reservations import ReservationHandler
from endpoints.payments import PaymentHandler
from endpoints.billing import BillingHandler

class Router:
    def __init__(self):
        self.routes = {
            'POST': [
                ("/register", AccountHandler),
                ("/login", AccountHandler),
                ("/parking-lots", ParkingLotHandler),
                ("/vehicles", VehicleHandler),
                ("/reservations", ReservationHandler),
                ("/payments", PaymentHandler),
            ],
            'PUT': [
                ("/profile", ProfileHandler),
                ("/parking-lots/", ParkingLotHandler),
                ("/vehicles/", VehicleHandler),
                ("/reservations/", ReservationHandler),
                ("/payments/", PaymentHandler),
            ],
            'DELETE': [
                ("/parking-lots/", ParkingLotHandler),
                ("/vehicles/", VehicleHandler),
                ("/reservations/", ReservationHandler),
            ],
            'GET': [
                ("/profile", ProfileHandler),
                ("/logout", AccountHandler),
                ("/parking-lots", ParkingLotHandler),
                ("/vehicles", VehicleHandler),
                ("/reservations", ReservationHandler),
                ("/payments", PaymentHandler),
                ("/billing", BillingHandler),
            ]
        }

    def get_handler(self, method, path):
        for route, handler in self.routes.get(method, []):
            if path.startswith(route):
                return handler
        return None

class MainHandler(BaseHTTPRequestHandler):
    router = Router()

    def _delegate(self, method):
        handler_cls = self.router.get_handler(method, self.path)
        if handler_cls:
            handler = handler_cls()
            handler.handle(self, method)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Endpoint not found")

    def do_POST(self):
        self._delegate('POST')

    def do_PUT(self):
        self._delegate('PUT')

    def do_DELETE(self):
        self._delegate('DELETE')

    def do_GET(self):
        self._delegate('GET')

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8000), MainHandler)
    print("Server running on http://localhost:8000")
    server.serve_forever()
