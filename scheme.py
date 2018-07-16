import serial
import sys
import os
import random
import time
import re
from colorama import Fore
from colorama import Style

####################
# variables to set
arduinoNumber = 10
start_number = 361
end_number = 500
timeToWaitOff = 3
timeToWaitOn = 3
extraInfo = "test"


key_length = 128
repetition_length = 15
parts_to_send = 8

enrolled_devices = 0
choice = "0"


cycles = end_number-start_number+1
arduinoCount = str(arduinoNumber)+"-"+str(timeToWaitOff)+"s-n"+str(end_number)+extraInfo
ignoreLines = 111   # in the current implementation the first 111 lines of returned data
# are unusable for PUF generation
cycleLocation = "/home/katanakiwi/opt/uhubctl/uhubctl"
workdir = "/home/katanakiwi/PycharmProjects/logger/"
savedir = workdir+"measurements/"+arduinoCount+"/"
auth_dir = workdir+"authenticated/"
# EOF variables
####################


def main():
    print()
    print("Welcome to the program.")
    while(1):
        new_Action()


def new_Action():
    print("\nWhat action do you want to perform?\n")
    print("1. Enroll a new device.")
    print("2. Authenticate a device.")
    print("3. List a device's properties")
    print("4. Remove an enrolled device")
    print("5. Change device ID")
    global choice
    if (choice == "0"):
        choice = input("Please select your choice: ")
    if choice == "1":
        Enroll_Device()
    elif choice == "2":
        Authenticate()
    elif choice == "3":
        List_Device()
    elif choice == "4":
        Remove_Device()
    elif choice == "5":
        change_ID()
    else:
        print("invalid choice entered...")
    choice = "0"


def Authenticate():
    print("Starting authentication phase")
    ser = Open_Serial()
    if ser == "noArduino":
        return
    ser.write(b"a")
    arduino_response = ser.readline()
    ID = arduino_response.decode("utf-8")
    ID = ID.rstrip()
    print("Arduino ID (response): ", ID)

    puf_file = auth_dir + "PUF_" + str(ID) + ".txt"
    ecc_file = auth_dir + "ECC_" + str(ID) + ".txt"
    key_file = auth_dir + "KEY_" + str(ID) + ".txt"
    if not os.path.exists(key_file):
        print("Arduino not enrolled; Aborting")
        return

    with open(key_file, "r") as text_file:
        saved_key = text_file.read()
        saved_key = saved_key[0:128]
    print("Printing saved key: \n", saved_key)
    with open(ecc_file, "r") as text_file:
        ecc_data = text_file.read()
    stripped_ecc = ecc_data.replace('\n', '')
    # print(stripped_ecc)
    # ser.write(bytes(stripped_ecc.encode('utf-8')))
    sector_size = int(key_length*repetition_length/parts_to_send)
    for b in range(0, parts_to_send, 1):
        ecc = stripped_ecc[b*sector_size:(b+1)*sector_size]
        print(b, " Sending ECC data:", ecc)
        time.sleep(0.105)
        ser.write(bytes(ecc.encode('utf-8')))

    print("Printing saved key: \n", saved_key)
    read_key_string = ser.readline()
    read_key = read_key_string.decode('utf-8')
    key = read_key.replace('Final key: ', '')
    key = key[0:key_length]
    print("Printing generated key: \n", key)
    if key == saved_key:
        print("\nAuthentication succesful!\n")
        corrected_bits = ser.readline()
        corrected_bits = corrected_bits.decode('utf-8')
        corrected_bits = corrected_bits.replace('Bits corrected: ', '')
        print("Amount of bits corrected: ", corrected_bits)
    else:
        print("ABORTED, KEY NOT MATCHING")


def Enroll_Device():
    # print("Enroll Device function not fully implemented yet!!")
    # powerCycle() #to be turned on later, only works with powercycle-able hub connected
    ser = Open_Serial()
    if ser == "noArduino":
        return
    ser.write(b"e")
    response = ser.readline()
    print(response.decode("utf-8"))
    new_ID = ask_new_ID()
    print("enrolling new arduino with ID: ", new_ID)
    print("Arduino response: ")
    ser.write(bytes([new_ID]))
    enroll_acknowledgement = ser.readline()
    # enroll_acknowledgement = enroll_acknowledgement.decode("utf-8")
    print(enroll_acknowledgement)

    log = ser.readline()
    tmp_file = workdir+"test.txt"
    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    with open(tmp_file, "w") as output:
        print(log, file=output)
    # print("Arduino output: \n", log.decode("utf-8"))
    PUF = Decode_Log(log)

    print(len(PUF))
    PUF_per_line = decode_per_line(log) # this is a per line spaced string of the PUF values
    # print("Decoded log:")
    # print(PUF_per_line)
    # print(len(PUF)/16)
    puf_file = auth_dir + "PUF_" + str(new_ID) + ".txt"
    ecc_file = auth_dir + "ECC_" + str(new_ID) + ".txt"
    key_file = auth_dir + "KEY_" + str(new_ID) + ".txt"

    if os.path.exists(puf_file) or os.path.exists(ecc_file) or os.path.exists(key_file):
        error_msg = input("This arduino ID is already present. Do you want to replace it? (yes/no)")
        if error_msg == "yes" or error_msg == "y":
            os.remove(puf_file)
            os.remove(ecc_file)
            os.remove(key_file)
        else:
            print("not replacing arduino id", new_ID)
            return

    with open(puf_file, "w") as text_file:
        print(PUF_per_line, file=text_file)
    key = get_repetition_key(PUF)
    ecc_data = get_ecc(PUF_per_line)

    with open(key_file, "w") as text_file:
        print(key, file=text_file)
    with open(ecc_file, "w") as text_file:
        print(ecc_data, file=text_file)
    # save ecc_data
    Close_Serial(ser)


def ask_new_ID():
    new_ID = input("Enter ID number for new Arduino: ")
    new_ID = int(new_ID)
    return new_ID


def Decode_Log(log):
    utf_log = log.decode("utf-8")
    log_hex = re.sub(r'(\t)(...\t)', r'\g<1>0\g<2>', utf_log)
    log_padded_lined = re.sub(r"[\t]", "\n", log_hex)
    # print(log_hexadecimal)
    log_bin = Hex2Bin(log_padded_lined)
    return log_bin


def decode_per_line(log):
    utf_log = log.decode("utf-8")
    log_hex = re.sub(r'(\t)(...\t)', r'\g<1>0\g<2>', utf_log)
    log_padded_lined = re.sub(r"[\t]", "\n", log_hex)
    # print(log_hexadecimal)
    log_bin = Hex2Bin(log_padded_lined)

    log_out = ""
    for a in range(0, key_length, 1):
        log_out = log_out + log_bin[a+15*a:16*a+15]
        if a != (key_length-1):
            log_out = log_out + "\n"
    return log_out


def get_ecc(PUF):
    ecc = ""
    # print(len(PUF))
    for a in range(0, key_length, 1):
        line = PUF[16*a:15+16*a]
        key = line[0]
        for b in range(0, len(line), 1):
            temp = bin(int(key, base=2) ^ int(line[b], base=2))
            ecc_line = "" + temp[2:]
            ecc = ecc + str(ecc_line)
        if a != (key_length-1):
            ecc = ecc + "\n"
    return ecc


def get_repetition_key(PUF):
    key_bits = ""
    for a in range(0, key_length, 1):
        line = PUF[a+15*a:14+16*a]
        key_bits = key_bits + str(line[0])
    print("Determined key:\t", key_bits, "\nKey length:\t\t", len(key_bits))
    return key_bits


def retrieve_key(PUF):
    key_bits = ""
    for a in range(0, key_length-1, 1):
        line = PUF[a+15*a:14+16*a]
        print(line)
        temp = 0
        for ch in line:
            if ch == 1:
                temp = temp + 1
        if round(temp/repetition_length, 0) == 1:
            key_bits = key_bits + "1"
        elif round(temp/repetition_length, 0) == 0:
            key_bits = key_bits + "0"
        else:
            print("error during key generation, wtf?")
        # print(key_bits)
    return key_bits


def decode_temp(log):
    log_hexadecimal = log.decode("utf-8")
    log_bin = Hex2Bin(log_hexadecimal)
    return log_bin


def get_ECC_Data(temp_id):
    ECC_data = ""
    with open(workdir+str(temp_id)+"_helper_data.txt", "r") as ecc_file:
        for line in ecc_file:
            ECC_data = ECC_data + line.strip('\n')
    return ECC_data


def get_Saved_Key(temp_id):
    temp_key = ""
    with open(workdir+str(temp_id)+"_key_data.txt", "r") as ecc_file:
        for line in ecc_file:
            temp_key = temp_key + line.strip('\n')
    return temp_key


def get_New_Key(ser):
    log = ser.readline()
    new_key = Extract_Key_From_PUF(Decode_Log(log))
    while len(new_key) < 128:
        new_key = "0" + new_key
    return new_key


def Extract_Key_From_PUF(full_PUF_response):
    return_key = ""
    for a in range(1, key_length+1, 1):
        PUF_response = full_PUF_response[(ignoreLines+a)*32:(ignoreLines+a)*32+repetition_length]
        key = PUF_response[0]
        key_bits = ""
        for b in range(1, repetition_length+1):
            key_bits = key_bits+str(key)
        temp2 = bin(int(key_bits, base=2) ^ int(PUF_response, base=2))
        helper_data = "" + temp2[2:]
        while len(helper_data) < repetition_length:
            helper_data = "0" + helper_data
        # print('bit ', a, ' of key')
        # print('\t PUF value: \t', PUF_response)
        # print('\t key: \t\t\t', key_bits)
        # print('\t ECC data: \t\t', helper_data)
        return_key = return_key + key
    return return_key


def Open_Serial():
    ser = serial.Serial()
    ser.baudrate = 115200
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    time.sleep(timeToWaitOn)
    arduino_location = getArduinoLocation()
    if arduino_location == "noArduino":
        print(Fore.RED + "It looks like no Arduino was connected" + Style.RESET_ALL)
        return "noArduino"
    ser.port = arduino_location
    ser.open()
    time.sleep(timeToWaitOn)
    return ser


def Close_Serial(ser):
    ser.close()


def change_ID():
    ser = Open_Serial()
    if ser == "noArduino":
        return
    ser.write(b"c")
    response = ser.readline()
    print(response.decode("utf-8"))
    new_ID = ask_new_ID()
    print("Changing ID to: ", new_ID)
    ser.write(bytes([new_ID]))
    enroll_acknowledgement = ser.readline()
    # enroll_acknowledgement = enroll_acknowledgement.decode("utf-8")
    print(enroll_acknowledgement)


def get_Next_ID():
    global enrolled_devices
    enrolled_devices = enrolled_devices + 1
    return int(enrolled_devices)


def Remove_Device():
    print("Remove Device function not implemented yet.")


def List_Device():
    print("Remove Device function not implemented yet.")
    print("list current list of devices, allow to select a device to print, then return to start")


def saveFiles(o, meas_count):
    binary_output_file = savedir + "bin" + str(meas_count) + ".txt"
    binary_output_file_per_line = savedir + "bin_perline" + str(meas_count) + ".txt"
    binary_output_file_spaced = savedir + "spaced" + str(meas_count) + ".txt"

    hex2BinFile(o, binary_output_file)
    hex2BinFilePerLine(o, binary_output_file_per_line)
    hex2BinFileSpaced(o, binary_output_file_spaced)


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
    return "noArduino"


def zeroPadAndSave(i, o):
    if os.path.exists(o):
        print("removing tempfile " + o)
        os.remove(o)
    # tmp = workdir + str(input)
    with open(i) as temp:
        for line in temp:
            while len(line) < 9:  # zeropads to up to 8 characters, adding leading zero's.
                line = "0" + line
            # print(line)
            with open(o, "a") as tempfile:
                tempfile.write(line)


def Hex2Bin(log):
    log_bin = ""
    for line in log:
        for ch in line:
            if ch == "0":
                log_bin = log_bin + "0000"
            elif ch == "1":
                log_bin = log_bin + "0001"
            elif ch == "2":
                log_bin = log_bin + "0010"
            elif ch == "3":
                log_bin = log_bin + "0011"
            elif ch == "4":
                log_bin = log_bin + "0100"
            elif ch == "5":
                log_bin = log_bin + "0101"
            elif ch == "6":
                log_bin = log_bin + "0110"
            elif ch == "7":
                log_bin = log_bin + "0111"
            elif ch == "8":
                log_bin = log_bin + "1000"
            elif ch == "9":
                log_bin = log_bin + "1001"
            elif ch == "A":
                log_bin = log_bin + "1010"
            elif ch == "B":
                log_bin = log_bin + "1011"
            elif ch == "C":
                log_bin = log_bin + "1100"
            elif ch == "D":
                log_bin = log_bin + "1101"
            elif ch == "E":
                log_bin = log_bin + "1110"
            elif ch == "F":
                log_bin = log_bin + "1111"
    return log_bin


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


def powerOff():
    print('shutting down Arduino')
# This .sh script makes a call to the 'uhubctl' program to turn the power on/off on port 2 of the only connected hub.
# The script should be edited/changed if more ports are connected
# Root permissions are needed on this file and are explicitly added in the system environment
#     os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOff.sh >/dev/null 2>&1')
    os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOff.sh')


def powerOn():
    print('starting up Arduino')
    # os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOn.sh >/dev/null 2>&1')
    os.system('sudo /home/katanakiwi/PycharmProjects/logger/powerOn.sh')


def powerCycle():
    powerOff()
    print("Waiting ", timeToWaitOff, " seconds")
    time.sleep(timeToWaitOff)
    powerOn()
    print("Waiting ", timeToWaitOn, " seconds")
    time.sleep(timeToWaitOn)


if __name__ == "__main__":
    main()
