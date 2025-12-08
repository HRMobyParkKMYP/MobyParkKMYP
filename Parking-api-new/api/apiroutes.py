from fastapi import FastAPI, HTTPException
from customlogger import Logger
import constants
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from account import account

class ApiResponse(BaseModel):
    StatusResponse: dict
    Content : Any

class Apiroutes:
    def __init__(self) -> None:
        self.App = FastAPI()
        self.log = Logger.getLogger("API")
        self.SetupEndpoints()
        self.SetupRoutes()


    def FormatResponse(self, status_response: dict, content : Any) -> ApiResponse:
        return ApiResponse(StatusResponse=status_response, Content=content)


    def StatusResponse(self, status: int) -> dict:
        messages = {
            200: "OK: The request has succeeded.",
            201: "Created: The request has succeeded and a new resource has been created.",
            204: "No Content: The server successfully processed the request and is not returning any content.",
            400: "Bad Request: The server could not understand the request due to invalid syntax.",
            404: "Not Found: The server can not find the requested resource.",
            500: "Internal Server Error: The server has encountered a situation it doesn't know how to handle."
        }
        return {"Status": status, "StatusMessage": messages.get(status, "Unknown status code.")}

    def tempDefaultResponse(self) -> dict:
        try:
            return self.FormatResponse(self.StatusResponse(201), {"status" : "success"})
        except Exception as e:
            return self.FormatResponse(self.StatusResponse(400), {"status" : "failed"})
    
    def SetupEndpoints(self) -> None:
        """Include all endpoint routers"""
        self.App.include_router(account.router, tags=["Account"])
        
    def SetupRoutes(self) -> None:

        @self.App.get("/", response_model=ApiResponse)
        async def root():
            return self.tempDefaultResponse()

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        # User

        @self.App.get("/profile", response_model=ApiResponse)
        async def get_profile():
            return self.tempDefaultResponse()

        @self.App.put("/profile", response_model=ApiResponse)
        async def update_profile():
            return self.tempDefaultResponse()

        # Parking Lot

        @self.App.post("/parking-lots", response_model=ApiResponse)
        async def create_parking_lot():
            return self.tempDefaultResponse()

        @self.App.get("/parking-lots", response_model=ApiResponse)
        async def get_parking_lots():
            return self.tempDefaultResponse()

        @self.App.get("/parking-lots/{id}", response_model=ApiResponse)
        async def get_parking_lot(id: str):
            return self.tempDefaultResponse()

        @self.App.put("/parking-lots/{id}", response_model=ApiResponse)
        async def update_parking_lot(id: str):
            return self.tempDefaultResponse()

        @self.App.delete("/parking-lots/{id}", response_model=ApiResponse)
        async def delete_parking_lot(id: str):
            return self.tempDefaultResponse()

        # Parking Lot Handling

        @self.App.post("/parking-lots/{id}/sessions/start", response_model=ApiResponse)
        async def start_parking_session(id: str):
            return self.tempDefaultResponse()

        @self.App.post("/parking-lots/{id}/sessions/stop", response_model=ApiResponse)
        async def stop_parking_session(id: str):
            return self.tempDefaultResponse()

        @self.App.get("/parking-lots/{id}/sessions", response_model=ApiResponse)
        async def get_parking_sessions(id: str):
            return self.tempDefaultResponse()

        @self.App.get("/parking-lots/{id}/sessions/{sid}", response_model=ApiResponse)
        async def get_parking_session(id: str, sid: str):
            return self.tempDefaultResponse()

        @self.App.delete("/parking-lots/{id}/sessions/{sid}", response_model=ApiResponse)
        async def delete_parking_session(id: str, sid: str):
            return self.tempDefaultResponse()

        # Reservations

        @self.App.post("/reservations", response_model=ApiResponse)
        async def create_reservation():
            return self.tempDefaultResponse()

        @self.App.put("/reservations/{id}", response_model=ApiResponse)
        async def update_reservation(id: str):
            return self.tempDefaultResponse()

        @self.App.get("/reservations/{id}", response_model=ApiResponse)
        async def get_reservation(id: str):
            return self.tempDefaultResponse()

        @self.App.delete("/reservations/{id}", response_model=ApiResponse)
        async def delete_reservation(id: str):
            return self.tempDefaultResponse()

        # Vehicles

        @self.App.post("/vehicles", response_model=ApiResponse)
        async def create_vehicle():
            return self.tempDefaultResponse()

        @self.App.get("/vehicles", response_model=ApiResponse)
        async def get_vehicles():
            return self.tempDefaultResponse()

        @self.App.get("/vehicles/{username}", response_model=ApiResponse)
        async def get_user_vehicles(username: str):
            return self.tempDefaultResponse()

        @self.App.put("/vehicles/{plate_id}", response_model=ApiResponse)
        async def update_vehicle(plate_id: str):
            return self.tempDefaultResponse()

        @self.App.delete("/vehicles/{plate_id}", response_model=ApiResponse)
        async def delete_vehicle(plate_id: str):
            return self.tempDefaultResponse()

        @self.App.post("/vehicles/{id}/entry", response_model=ApiResponse)
        async def vehicle_entry(id: str):
            return self.tempDefaultResponse()

        @self.App.get("/vehicles/{id}/reservations", response_model=ApiResponse)
        async def get_vehicle_reservations(id: str):
            return self.tempDefaultResponse()

        @self.App.get("/vehicles/{id}/history", response_model=ApiResponse)
        async def get_vehicle_history(id: str):
            return self.tempDefaultResponse()

        # Payments

        @self.App.post("/payments", response_model=ApiResponse)
        async def create_payment():
            return self.tempDefaultResponse()

        @self.App.post("/payments/refund", response_model=ApiResponse)
        async def refund_payment():
            return self.tempDefaultResponse()

        @self.App.put("/payments/{transaction}", response_model=ApiResponse)
        async def complete_payment(transaction: str):
            return self.tempDefaultResponse()

        @self.App.get("/payments", response_model=ApiResponse)
        async def get_payments():
            return self.tempDefaultResponse()

        @self.App.get("/payments/{username}", response_model=ApiResponse)
        async def get_user_payments(username: str):
            return self.tempDefaultResponse()

        # Billing

        @self.App.get("/billing", response_model=ApiResponse)
        async def get_billing():
            return self.tempDefaultResponse()

        @self.App.get("/billing/{username}", response_model=ApiResponse)
        async def get_user_billing(username: str):
            return self.tempDefaultResponse()

def run():
    print("run")
    api_instance = Apiroutes()
    return api_instance.App