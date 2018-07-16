startbit = 1024
length = 128
for a in range(startbit,startbit+length,1):
    string = "#define PUF"+str(a-(startbit-1))+" (*(volatile uint16_t*)0x"+str(1024+(a-1024)*2)+")"
    string2 = "PUF"+str(a-(startbit-1))+" = (*(volatile uint16_t*)0x"+str(1024+(a-1024)*2)+");"
    print(string)
    print(string2)