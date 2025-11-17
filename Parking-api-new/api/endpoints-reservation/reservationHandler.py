from customlogger import Logger
from fastapi import FastAPI
from apiroutes import ApiResponse
from reservationUtils import reservationUtils

class ReservationHandler:

    def __init__(self, app : FastAPI):
        self.logger = Logger.getLogger("ReservationHandler")
        self.App = app
        self.Utils = reservationUtils()
        self.SetupRoutes()


    def SetupRoutes(self) -> None:

        @self.App.post("/reservations", response_model=ApiResponse)
        async def create_reservation():
            """
            creates a reservation in the db
            """
            return self.tempDefaultResponse()


        @self.App.put("/reservations/{id}", response_model=ApiResponse)
        async def update_reservation(id: str):
            """
            updates a reservation in the db by id
            """
            return self.tempDefaultResponse()


        @self.App.get("/reservations/{id}", response_model=ApiResponse)
        async def get_reservation(id: str):
            """
            gets a reservation from db by an id
            """
            return self.tempDefaultResponse()


        @self.App.delete("/reservations/{id}", response_model=ApiResponse)
        async def delete_reservation(id: str):
            """
            removes a reservation from the db by id
            """
            return self.tempDefaultResponse()
