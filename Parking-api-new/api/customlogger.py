import logging
import logging.handlers
import datetime as dt
import os
import constants

class Logger:

    def __init__(self):
        self.log_file_path = self.setupLogFile()


    def setupLogFile(self) -> str:
        """
        sets up the logfile

        :return: path to the logfile
        :rtype: str
        """

        log_time = dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file_path = os.path.join(constants.MAIN_DIR, constants.SYSTEMLOGS_DIR, f'Log_{log_time}.txt')
        
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=constants.MAX_LOG_SIZE,
            backupCount=100,
            mode='a'
        )

        handler.doRollover = self.customDoRollover(handler)
        
        formatter = logging.Formatter('[%(asctime)s] - [%(name)s] -- %(message)s')
        handler.setFormatter(formatter)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        logging.info("Logging initialized in file: %s", log_file_path)
        
        return log_file_path
    

    def customDoRollover(self, handler : logging.handlers.RotatingFileHandler):
        """
        Copys the basic doRollover function from logging lib, but adds a message to the end of the old logfile
        """
        originalDoRollover = handler.doRollover

        def newDoRollover():
            originalDoRollover()
            self.logger.info("Log reached maximum file size, transferring to new log file.")

        return newDoRollover


    @staticmethod
    def getLogger(module_name):
        """
        Return a logger for the specified module name.
        """
        return logging.getLogger(module_name)