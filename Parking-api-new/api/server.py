import asyncio
import threading
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
        self.logger.info("Starting API")
        api = run()  
        uvicorn.run(api, host=constants.UVICORN_HOST_IP, port=constants.UVICORN_HOST_PORT)


    async def main(self) -> None:

        try:
            apiThread = threading.Thread(target=self.runApi)
            apiThread.start()

        except Exception as e:
            self.logger.info(e)


if __name__ == "__main__":

    main = Main()
    asyncio.run(main.main())