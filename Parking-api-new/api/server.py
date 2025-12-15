import uvicorn
import constants
from customlogger import Logger
from apiroutes import Apiroutes, run

class Main():

    def __init__(self):
        try:
            self.logger = Logger().getLogger("Main")
            self.logger.info("Initializing Main class")

        except Exception as e:
            self.logger.info(e)

    def runApi(self):
        """
        runs an instance of fastapi and serves it with uvicorn
        """
        self.logger.info("Starting API")
        api = run()
        uvicorn.run(api, host=constants.UVICORN_HOST_IP, port=constants.UVICORN_HOST_PORT)


if __name__ == "__main__":

    main = Main()
    main.runApi()