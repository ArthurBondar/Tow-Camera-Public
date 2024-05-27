#!/usr/bin/python2

import datetime, subprocess, os, sys
from time import sleep
import logging

# Create instance of log class
logging.basicConfig(
        filename=str(sys.argv[1]),
        filemode='a',
        format='%(asctime)s %(module)-8s %(levelname)-10s %(message)s',
        level=logging.DEBUG
)

print "Debugging logging class"
# Running a series test prints to the log

log=logging.getLogger(__name__)

logging.debug("This is debug")
logging.info("This is info")
logging.warning("This is warning")
logging.error("This is error")
logging.critical("This is critical")

log.setLevel(logging.INFO)
logging.debug("This is debug")
logging.info("This is info")
logging.warning("This is warning")
logging.error("This is error")
logging.critical("This is error")

log.setLevel(logging.WARNING)
logging.debug("This is debug")
logging.info("This is info")
logging.warning("This is warning")
logging.error("This is error")
logging.critical("This is error")

log.setLevel(logging.ERROR)
logging.debug("This is debug")
logging.info("This is info")
logging.warning("This is warning")
logging.error("This is error")
logging.critical("This is error")

log.setLevel(logging.CRITICAL)
logging.debug("This is debug")
logging.info("This is info")
logging.warning("This is warning")
logging.error("This is error")
logging.critical("This is error")

logging.shutdown()
# debug finished
print "Debug session finished"
exit()

