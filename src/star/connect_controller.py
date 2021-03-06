#! /usr/bin/python
# The entry point of our module
import serial, sys, urllib, urllib3, json, time
import requests
from uber_connect import call_uber, uber_time_estimate, uber_price_estimate
from firebase import firebase
from Firebase_util import putIntoFirebaseUber
import Firebase_util as fire
import connect_here as here
import connect_twilio as twilio
from threading import Thread

requests.packages.urllib3.disable_warnings()
initialTouched = False
leftToRight = False
topToBottom = False
requested = True
maxTries = 50

device_name = '/dev/cu.usbserial-FTGQJ7IM'
baud_rate = 115200

# Set up the serial port connection
ser = serial.Serial(device_name, baud_rate)

class Shape:  # define parent class
    def identifyShape(self):
        print 'This is super class, never called'

def verifyInitalTouch(c):
    global initialTouched
    if c == 'touchHold' or c == 'touchpadAreaPressed':
        initialTouched = True
        return True
    elif initialTouched == True:
        return True
    else:
        return False

def increasingY():
    newY = 0
    oldY = -1
    start = 1
    while True:
        raw_data = ser.readline()
        parts = raw_data.split()
        command = parts[0]
        params = dict((k, int(v)) for k, v in (p.split(':') for p in parts[1:]))
        if 'y' not in params:
            continue
        newY = params['y']
        if (start == 1):
            if newY < 110:
                start = 0
            else:
                return False
        if command == 'touchAt':
            if newY >= oldY:
                oldY = newY
                if newY > 320:
                    return True
                else:
                    continue
        return False

def verifyTopToBottomSwipe():
    while True:
        raw_data = ser.readline()
        parts = raw_data.split()
        command = parts[0]
        #  print "TB--", command, params
        if command == 'swipeDown':
            if increasingY():
                return True
            else:
                return False
    return False

def increasingX():
    newX = 0
    oldX = -1
    start = 1
    while True:
        raw_data = ser.readline()
        parts = raw_data.split()
        command = parts[0]
        params = dict((k, int(v)) for k, v in (p.split(':') for p in parts[1:]))
        if 'x' not in params:
            continue
        newX = params['x']
        if (start == 1):
            if newX < 140:
                start = 0
            else:
                return False
        if command == 'touchAt':
            if newX >= oldX:
                oldX = newX
                if newX > 250:
                    return True
                else:
                    continue
        return False

def verifyLeftToRightSwipe():
    while True:
        raw_data = ser.readline()
        parts = raw_data.split()
        command = parts[0]
        if command == 'swipeRight':
            if increasingX():
                return True
            else:
                return False
    return False

class PlusSymbol(Shape):
    def dumm(yself):
        print "dummy"
    def identifyShape(self):
        global initialTouched
        global requested
        numberOfTimesTried = 0
        print "Starting Touch Auth"
        while True:
            if (numberOfTimesTried > maxTries and requested):
                print "Ubering you"
                getCurrentLocation()
                requested = False
                fire.putIntoFirebaseUberState("yes")
            raw_data = ser.readline()
            parts = raw_data.split()
            command = parts[0]
            params = dict((k, int(v)) for k, v in (p.split(':') for p in parts[1:]))
            # Print for debugging
            print command, params
            if verifyInitalTouch(command) or initialTouched:
                if verifyTopToBottomSwipe():
                    print "Initial auth done."
                    if verifyLeftToRightSwipe():
                        print "You're successful in authenticating your soberness, drive!!"
                        fire.putIntoFirebaseUberState("no")
                    return True

            else:
                print "Please swipe correctly"
                numberOfTimesTried += 1
                initialTouched = False

            sys.stdout.flush()

def getCurrentLocation():
    url = "http://172.31.99.3/vehicle"
    response = urllib.urlopen(url)
    carData = json.loads(response.read())
    GPS_Latitude = carData['GPS_Latitude']
    GPS_Longitude = carData['GPS_Longitude']

    putIntoFirebaseUber(GPS_Latitude, GPS_Longitude)

    uber_time_estimate(GPS_Latitude, GPS_Longitude)

    uber_price_estimate(GPS_Latitude, GPS_Longitude)

    twilio.send_msg()

def pushToFireBaseBulk():
    print "Fire Base started"
    url = "http://172.31.99.3/vehicle"
    response = urllib.urlopen(url);
    carData = json.loads(response.read())
    fire.putIntoFirebaseCarBattery_Level(carData['Battery_Level'])
    fire.putIntoFirebaseCarHonk_State(carData['Honk_State'])
    fire.putIntoFirebaseCarFuel_Consumption(carData['Fuel_Consumption'])
    fire.putIntoFirebaseCarAccelerator_Pedal(carData['Accelerator_Pedal'])
    fire.putIntoFirebaseCarInside_Temperature(carData['Inside_Temperature'])
    fire.putIntoFirebaseCarFuel_Level(carData['Fuel_Level'])
    fire.putIntoFirebaseCarOutside_Air_Temperature(carData['Outside_Air_Temperature'])
    fire.putIntoFirebaseCarOdometer(carData['Odometer'])

    fire.putIntoFirebaseCarDoor_State_Front_Left(carData['Door_State_Front_Left'])
    fire.putIntoFirebaseCarDoor_State_Front_Right(carData['Door_State_Front_Right'])
    fire.putIntoFirebaseCarDoor_State_Rear_Left(carData['Door_State_Rear_Left'])
    fire.putIntoFirebaseCarDoor_State_Rear_Right(carData['Door_State_Rear_Right'])

    fire.putIntoFirebaseCarTire_Pressure_Front_Left(carData['Tire_Pressure_Front_Left'])
    fire.putIntoFirebaseCarTire_Pressure_Front_Right(carData['Tire_Pressure_Front_Right'])
    fire.putIntoFirebaseCarTire_Pressure_Rear_Left(carData['Tire_Pressure_Rear_Left'])
    fire.putIntoFirebaseCarTire_Pressure_Rear_Right(carData['Tire_Pressure_Rear_Right'])

    fire.putIntoFirebaseCarTimestamp(carData['Timestamp'])
    fire.putIntoFirebaseCarFuel_Level_Critical(carData['Fuel_Level_Critical'])
    fire.putIntoFirebaseCarVehicle_Speed(carData['Vehicle_Speed'])
    fire.putIntoFirebaseCarIgnition_State(carData['Turn_Indicator_State'])
    fire.putIntoFirebaseCarTurn_Indicator_State(carData['Turn_Indicator_State'])

    here.get_speedLimit(carData['GPS_Latitude'], carData['GPS_Longitude'])

def threadBack():
        while True:
            pushToFireBaseBulk()

if __name__ == "__main__":
    raw_data = ser.readline()
    symbol = PlusSymbol()
    symbol.identifyShape()
    firebase_thread = Thread(target=threadBack(), args=())
    firebase_thread = True
    firebase_thread.start()

