from customlogger import Logger
from apiroutes import ApiResponse
import constants
import sqlite3

class reservationUtils:

    def __init__(self):
        self.logger = Logger.getLogger("reservationUtils")


    def getReservation(id: int) -> ApiResponse:
        pass
    