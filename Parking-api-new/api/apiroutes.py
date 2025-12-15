from fastapi import FastAPI, HTTPException
from customlogger import Logger
import constants
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from account import account
from vehicle import vehicle
from parking_lots import parking_lots
from utils.database_utils import get_db_path

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
        self.App.include_router(vehicle.router, tags=["Vehicle"])
        self.App.include_router(parking_lots.router, tags=["Parking Lots"])
        
    def SetupRoutes(self) -> None:

        @self.App.get("/", response_model=ApiResponse)
        async def root():
            return self.tempDefaultResponse()

        @self.App.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        @self.App.get("/debug/db-info")
        async def db_info():
            """Debug endpoint to verify which database is being used"""
            return {
                "test_mode": os.environ.get('TEST_MODE', 'false'),
                "database_path": get_db_path(),
                "database_name": os.path.basename(get_db_path())
            }
        # User

        @self.App.get("/profile", response_model=ApiResponse)
        async def get_profile():
            return self.tempDefaultResponse()

        @self.App.put("/profile", response_model=ApiResponse)
        async def update_profile():
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

        # Vehicles - handled by vehicle router

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