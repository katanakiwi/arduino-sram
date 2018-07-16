import serial
import sys
import os
# import pickle
# from serial import Serial
# import subprocess
import time
import re

####################
# variables to set
arduinoNumber = "repetition_code"
start_number = 1
end_number = 1
timeToWaitOff = 20
timeToWaitOn = 6
extraInfo = ""


cycles = end_number-start_number+1
arduinoCount = str(arduinoNumber)+"-"+str(timeToWaitOff)+"s-n"+str(end_number)+extraInfo
ignoreLines = 111   # in the current implementation the first 111 lines of returned data
                    # are unusable for PUF generation
cycleLocation = "/home/katanakiwi/opt/uhubctl/uhubctl"
workdir = "/home/katanakiwi/PycharmProjects/logger/"
savedir = workdir+"measurements/"+arduinoCount+"/"
# EOF variables
####################


def main():
    ser = serial.Serial()
    ser.baudrate = 115200
    print()
    print('Starting program...')
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    powerOn()
    time.sleep(timeToWaitOn)

    for measurement_count in range(start_number, end_number+1, 1):
        arduino_location = getArduinoLocation()
        print("Starting measurement: " + str(measurement_count))
        ser.port = arduino_location
        ser.open()
        log = ser.readline()
        ser.close()

        # decoded_log = log.decode("utf-8")
        decoded_log = re.sub(r"[\t]", "\n", log.decode("utf-8"))

        tempfile = workdir + "tempfile.txt"
        with open(tempfile, "w") as text_file:
            print(decoded_log, file=text_file)

        # print('writing PUF response to file')
        outputfile = savedir + "log" + str(measurement_count) + ".txt"
        if os.path.exists(outputfile):
            sys.exit("Duplicate found, not overwriting, exiting")
        zeroPadAndSave(tempfile, outputfile)
        os.remove(tempfile)     # removes temporary file with un-zeropadded data
        saveFiles(outputfile, measurement_count)
        if measurement_count < end_number:
            powerOff()
            time.sleep(timeToWaitOff)
            powerOn()
            time.sleep(timeToWaitOn)

    # analyzeData()


def saveFiles(o, meas_count):
    binaryOutputFile = savedir + "bin" + str(meas_count) + ".txt"
    binaryOutputFilePerLine = savedir + "bin_perline" + str(meas_count) + ".txt"
    binaryOutputFileSpaced = savedir + "spaced" + str(meas_count) + ".txt"

    hex2BinFile(o, binaryOutputFile)
    hex2BinFilePerLine(o, binaryOutputFilePerLine)
    hex2BinFileSpaced(o, binaryOutputFileSpaced)


def powerOff():
    print('shutting down')
# This .sh script makes a call to the 'uhubctl' program to turn the power on/off on port 2 of the only connected hub.
# The script should be edited/changed if more ports are connected
# Root permissions are needed on this file and are explicitly added in the system environment
    os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOff.sh >/dev/null 2>&1')


def powerOn():
    print('starting up')
    os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOn.sh >/dev/null 2>&1')


def getArduinoLocation():
    loc = '/dev/ttyACM'
    for j in range(0, 9, 1):
        loc += str(j)
        if os.path.exists(loc):
            # print('location ' + str(j) + ' found, hooking arduino to location:')
            # print(loc)
            return loc
        else:
            loc = loc[:-1]


def zeroPadAndSave(i, o):
    if os.path.exists(o):
        print("removing tempfile " + o)
        os.remove(o)
    # tmp = workdir + str(input)
    with open(i) as temp:
        for line in temp:
            while len(line) < 9:     # zeropads to up to 8 characters, adding leading zero's.
                line = "0" + line
            # print(line)
            with open(o, "a") as tempfile:
                tempfile.write(line)


def hex2BinFile(i, o):
    if os.path.exists(o):
        os.remove(o)
    with open(i) as input_file:
        with open(o, "a") as output_file:
            for line in input_file:
                for ch in line:
                    if ch == "0": output_file.write("0000")
                    elif ch == "1": output_file.write("0001")
                    elif ch == "2": output_file.write("0010")
                    elif ch == "3": output_file.write("0011")
                    elif ch == "4": output_file.write("0100")
                    elif ch == "5": output_file.write("0101")
                    elif ch == "6": output_file.write("0110")
                    elif ch == "7": output_file.write("0111")
                    elif ch == "8": output_file.write("1000")
                    elif ch == "9": output_file.write("1001")
                    elif ch == "A": output_file.write("1010")
                    elif ch == "B": output_file.write("1011")
                    elif ch == "C": output_file.write("1100")
                    elif ch == "D": output_file.write("1101")
                    elif ch == "E": output_file.write("1110")
                    elif ch == "F": output_file.write("1111")


def hex2BinFileSpaced(i, o):
    if os.path.exists(o):
        os.remove(o)
    with open(i) as input_file:
        with open(o, "a") as output_file:
            for line in input_file:
                for ch in line:
                    if ch == "0": output_file.write("0 0 0 0 ")
                    elif ch == "1": output_file.write("0 0 0 1 ")
                    elif ch == "2": output_file.write("0 0 1 0 ")
                    elif ch == "3": output_file.write("0 0 1 1 ")
                    elif ch == "4": output_file.write("0 1 0 0 ")
                    elif ch == "5": output_file.write("0 1 0 1 ")
                    elif ch == "6": output_file.write("0 1 1 0 ")
                    elif ch == "7": output_file.write("0 1 1 1 ")
                    elif ch == "8": output_file.write("1 0 0 0 ")
                    elif ch == "9": output_file.write("1 0 0 1 ")
                    elif ch == "A": output_file.write("1 0 1 0 ")
                    elif ch == "B": output_file.write("1 0 1 1 ")
                    elif ch == "C": output_file.write("1 1 0 0 ")
                    elif ch == "D": output_file.write("1 1 0 1 ")
                    elif ch == "E": output_file.write("1 1 1 0 ")
                    elif ch == "F": output_file.write("1 1 1 1 ")


def hex2BinFilePerLine(i, o):
    if os.path.exists(o):
        os.remove(o)
    with open(i) as input_file:
        with open(o, "a") as output_file:
            for line in input_file:
                for ch in line:
                    if ch == "0": output_file.write("0\n0\n0\n0\n")
                    elif ch == "1": output_file.write("0\n0\n0\n1\n")
                    elif ch == "2": output_file.write("0\n0\n1\n0\n")
                    elif ch == "3": output_file.write("0\n0\n1\n1\n")
                    elif ch == "4": output_file.write("0\n1\n0\n0\n")
                    elif ch == "5": output_file.write("0\n1\n0\n1\n")
                    elif ch == "6": output_file.write("0\n1\n1\n0\n")
                    elif ch == "7": output_file.write("0\n1\n1\n1\n")
                    elif ch == "8": output_file.write("1\n0\n0\n0\n")
                    elif ch == "9": output_file.write("1\n0\n0\n1\n")
                    elif ch == "A": output_file.write("1\n0\n1\n0\n")
                    elif ch == "B": output_file.write("1\n0\n1\n1\n")
                    elif ch == "C": output_file.write("1\n1\n0\n0\n")
                    elif ch == "D": output_file.write("1\n1\n0\n1\n")
                    elif ch == "E": output_file.write("1\n1\n1\n0\n")
                    elif ch == "F": output_file.write("1\n1\n1\n1\n")


if __name__ == "__main__":
    main()
