length = 128
for a in range(1,length+1,1):
    string = "Serial.print(PUF"+str(a)+", BIN);"
    print(string)
    print("Serial.print(F(\"\\n\"));")