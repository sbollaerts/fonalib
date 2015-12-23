#!/usr/bin/python

from fonalib import Fona

PHONE_NUMBER = "{Your phone number here}"

FONA_PORT = "/dev/ttyAMA0"
FONA_SPEED = 115200
FONA_PIN = 4250
FONA_VERBOSE = True

fona = Fona(FONA_PORT, FONA_SPEED, FONA_PIN, FONA_VERBOSE)
if fona.status == Fona.STATUS_IDLE:
	fona.send(PHONE_NUMBER, "Hello, World!")
print("+++ END-OF-EXECUTION +++") 
