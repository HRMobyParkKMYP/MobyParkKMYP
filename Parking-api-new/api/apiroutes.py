from fastapi import FastAPI, HTTPException
from customlogger import Logger
import constants
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from endpoints.account import router as account
from endpoints.profile import router as profile
from endpoints.vehicle import router as vehicle
from endpoints.payments import router as payments
from endpoints.parking_lots import router as parking_lots
from utils.database_utils import get_db_path
from endpoints.billing import router as billing
from endpoints.reservations import router as reservations
from endpoints.discounts import router as discounts

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
        self.App.include_router(account, tags=["Account"])
        self.App.include_router(profile, tags=["Profile"])        
        self.App.include_router(vehicle, tags=["Vehicle"])
        self.App.include_router(payments, tags=["Payment"])
        self.App.include_router(billing, tags=["Billing"])
        self.App.include_router(parking_lots, tags=["Parking Lots"])
        self.App.include_router(reservations, tags=["Reservations"])
        self.App.include_router(discounts, tags=["Discounts"])
        
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

def run():
    print("run")
    api_instance = Apiroutes()
    return api_instance.App