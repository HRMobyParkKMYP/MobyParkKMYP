import uvicorn
import constants
import os
from customlogger import Logger
from apiroutes import Apiroutes, run
from utils.database_utils import get_db_path

class Main():

    def __init__(self):
        try:
            self.logger = Logger().getLogger("Main")
            self.logger.info("Initializing Main class")
            # Show which database is being used
            test_mode = os.environ.get('TEST_MODE', 'false')
            db_path = get_db_path()
            self.logger.info(f"TEST_MODE={test_mode}")
            self.logger.info(f"Using database: {db_path}")

        except Exception as e:
            self.logger.info(e)

    def runApi(self):
        self.logger.info("Starting API")
        api = run()
        uvicorn.run(api, host=constants.UVICORN_HOST_IP, port=constants.UVICORN_HOST_PORT)


if __name__ == "__main__":

    main = Main()
    main.runApi()