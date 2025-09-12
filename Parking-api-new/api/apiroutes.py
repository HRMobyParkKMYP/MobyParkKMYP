from fastapi import FastAPI, HTTPException
from customlogger import Logger
import constants
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ApiResponse(BaseModel):
    StatusResponse: dict
    Content : Any

class Apiroutes:
    def __init__(self) -> None:
        self.App = FastAPI()
        self.log = Logger.getLogger("API")
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

    # Defines all the routes for the API
    def SetupRoutes(self) -> None:

        @self.App.get("/", response_model=ApiResponse)
        async def root():
            return self.FormatResponse(self.StatusResponse(200), "Hello World!")


        # allows users to set their auth key via the frontend securely
        @self.App.post("/v1/internal/apikey", response_model=ApiResponse)
        async def apikey(internalBearer : str):
            try:
                if internalBearer != constants.IBT:
                    self.log.warning(f"attempted unauthorized access to apikey")
                    return self.FormatResponse(self.StatusResponse(400), {"status" : "Unauthorized access"})
                
                return self.FormatResponse(self.StatusResponse(201), {"status" : "success"})
            
            except Exception as e:
                self.log.error(f"Failed to set auth key: {e}")
                return self.FormatResponse(self.StatusResponse(400), {"status" : "failed"})
        

        # allows users to get their auth key via the frontend securely
        @self.App.get("/v1/internal/apikey", response_model=ApiResponse)
        async def apikey(internalBearer : str):
            try:
                if internalBearer != constants.IBT:
                    self.log.warning(f"attempted unauthorized access to apikey")
                    return self.FormatResponse(self.StatusResponse(400), {"status" : "Unauthorized access"})

                return self.FormatResponse(self.StatusResponse(201), {"status" : "success"})
            
            except Exception as e:
                self.log.error(f"Failed to get auth key: {e}")
                return self.FormatResponse(self.StatusResponse(400), {"status" : "failed"})



def run():
    print("run")
    api_instance = Apiroutes()
    return api_instance.App