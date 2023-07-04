import sys
import argparse

class NetworkRx_Obj:
    def __init__(self):
        self.numCh = 0
        self.retryCount = -1
        self.fileName = [None] * 16
        self.dataBuf = None
        self.serverPort = None
        self.dstIpAddr = None
        self.srcIpAddr = None
        self.usetfdtp = 0
        self.verbose = 0
        self.no_loop = 0

gNetworkRx_obj = NetworkRx_Obj()

class NetworkRx_CmdHeader:
    def __init__(self):
        self.header = None
        self.chNum = None
        self.dataSize = None
        self.numBuf = None

def ShowUsage():
    print(" ")
    print("# ")
    print("# network_rx --host_ip <ipaddr> --target_ip <ipaddr> [--port <server port> --usetfdtp --verbose --no_loop --delay <delay in secs> --retry_count <no of retries>] --files <CH0 file> <CH1 file> ... ")
    print("# Ex- ../bin/network_rx.exe --host_ip <ipaddr> --target_ip  <ipaddr> --port 29172 --usetfdtp  --files ../test_file.yuv ")
    print("# ")
    print("# (c) Texas Instruments 2014")
    print("# ")
    sys.exit(0)

def OpenDataFile(pHeader):
    chId = pHeader.chNum

    if pHeader.chNum >= gNetworkRx_obj.numCh:
        print("# ERROR: Incorrect Channel number [%s]" % gNetworkRx_obj.fileName[chId])
        return -1

    if gNetworkRx_obj.fd[chId] is None:
        gNetworkRx_obj.frameCount[chId] = 0
        try:
            gNetworkRx_obj.fd[chId] = open(gNetworkRx_obj.fileName[chId], "wb")
        except IOError:
            print("# ERROR: Unable to open file [%s]" % gNetworkRx_obj.fileName[chId])
            pHeader.dataSize = 0
            return -1

    return 0

def WriteBytes(pHeader):
    chId = pHeader.chNum

    bytesWr = gNetworkRx_obj.fd[chId].write(gNetworkRx_obj.dataBuf[:pHeader.dataSize])
    if bytesWr != pHeader.dataSize:
        print("# ERROR: CH%d: File [%s] write failed !!!" % (chId, gNetworkRx_obj.fileName[chId]))
        gNetworkRx_obj.fd[chId].close()
        gNetworkRx_obj.fd[chId] = None
        gNetworkRx_obj.frameCount[chId] = 0
        return -1

    if gNetworkRx_obj.verbose:
        print("# INFO: DATA: CH%d: Frame%d: %d bytes" % (pHeader.chNum, gNetworkRx_obj.frameCount[chId], pHeader.dataSize))

    gNetworkRx_obj.frameCount[chId] += 1
    gNetworkRx_obj.totalDataSize[chId] += pHeader.dataSize

    if gNetworkRx_obj.frameCount[chId] and (gNetworkRx_obj.frameCount[chId] % 10) == 0:
        print("# INFO: DATA: CH%d: Recevied %d frames, %10.2f MB" % (pHeader.chNum, gNetworkRx_obj.frameCount[chId], gNetworkRx_obj.totalDataSize[chId] / (1024.0 * 1024)))

    return 0

def WriteData(pHeader):
    status = 0

    if gNetworkRx_obj.no_loop:
        if OpenDataFile(pHeader) < 0:
            return -1
        status = WriteBytes(pHeader)
    else:
        while status >= 0 and pHeader.numBuf > 0:
            if OpenDataFile(pHeader) < 0:
                return -1
            status = WriteBytes(pHeader)
            pHeader.numBuf -= 1

    return status

def ReadData(sock, pHeader):
    try:
        recvBytes = sock.recv(pHeader.dataSize)
    except:
        print("# ERROR: socket.recv() failed")
        return -1

    if len(recvBytes) != pHeader.dataSize:
        print("# ERROR: DATA: CH%d: expected %d bytes, received %d bytes" % (pHeader.chNum, pHeader.dataSize, len(recvBytes)))
        return -1

    if gNetworkRx_obj.usetfdtp:
        try:
            sock.send(b"\x7F\x7F")
        except:
            print("# ERROR: TFDTP: CH%d: sock.send() failed" % pHeader.chNum)
            return -1

    gNetworkRx_obj.dataBuf = recvBytes

    return 0

def ReadCmdHeader(sock, pHeader):
    try:
        recvBytes = sock.recv(8)
    except:
        print("# ERROR: socket.recv() failed")
        return -1

    if len(recvBytes) != 8:
        print("# ERROR: CMD_HEADER: CH%d: expected 8 bytes, received %d bytes" % (pHeader.chNum, len(recvBytes)))
        return -1

    pHeader.header = recvBytes
    pHeader.chNum = ord(recvBytes[4])
    pHeader.dataSize = (ord(recvBytes[5]) << 24) + (ord(recvBytes[6]) << 16) + (ord(recvBytes[7]) << 8)
    pHeader.numBuf = ord(recvBytes[2])

    return 0

def ConnectToServer():
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except:
        print("# ERROR: socket.socket() failed")
        return None

    try:
        sock.connect((gNetworkRx_obj.dstIpAddr, gNetworkRx_obj.serverPort))
    except:
        print("# ERROR: socket.connect() failed")
        sock.close()
        return None

    return sock

def CloseConnection(sock):
    sock.close()

def RecvData():
    cmdHeader = NetworkRx_CmdHeader()
    sock = ConnectToServer()

    if sock is None:
        return

    while ReadCmdHeader(sock, cmdHeader) >= 0:
        if cmdHeader.chNum >= gNetworkRx_obj.numCh:
            print("# ERROR: Incorrect Channel number [%d]" % cmdHeader.chNum)
            break

        if ReadData(sock, cmdHeader) < 0:
            break

        if WriteData(cmdHeader) < 0:
            break

        if gNetworkRx_obj.retryCount >= 0 and gNetworkRx_obj.retryCount <= gNetworkRx_obj.frameCount[cmdHeader.chNum]:
            break

    CloseConnection(sock)

def ParseCmdLineArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host_ip", help="Host IP address")
    parser.add_argument("--target_ip", help="Target IP address")
    parser.add_argument("--port", type=int, help="Server port number", default=29172)
    parser.add_argument("--usetfdtp", action="store_true", help="Use TFDTP for data transfer")
    parser.add_argument("--verbose", action="store_true", help="Print verbose information")
    parser.add_argument("--no_loop", action="store_true", help="Do not loop for continuous data reception")
    parser.add_argument("--delay", type=int, help="Delay in seconds before connecting to server", default=0)
    parser.add_argument("--retry_count", type=int, help="Number of times to retry receiving data", default=-1)
    parser.add_argument("--files", nargs='+', help="List of files to receive data for each channel")

    args = parser.parse_args()

    if not args.host_ip or not args.target_ip or not args.files:
        ShowUsage()

    gNetworkRx_obj.dstIpAddr = args.host_ip
    gNetworkRx_obj.srcIpAddr = args.target_ip
    gNetworkRx_obj.serverPort = args.port
    gNetworkRx_obj.usetfdtp = 1 if args.usetfdtp else 0
    gNetworkRx_obj.verbose = 1 if args.verbose else 0
    gNetworkRx_obj.no_loop = 1 if args.no_loop else 0
    gNetworkRx_obj.retryCount = args.retry_count

    gNetworkRx_obj.numCh = len(args.files)
    if gNetworkRx_obj.numCh > 16:
        print("# ERROR: Maximum number of channels supported is 16")
        ShowUsage()

    for i in range(gNetworkRx_obj.numCh):
        gNetworkRx_obj.fileName[i] = args.files[i]

if __name__ == "__main__":
    ParseCmdLineArgs()
    RecvData()
