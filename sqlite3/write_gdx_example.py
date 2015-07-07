from gdxcc import *
import sys
import os

numberParams = len(sys.argv)
if numberParams < 2 or numberParams > 3:
    print "**** Usage:", sys.argv[0], "sysDir [gdxinfn]"
    os._exit(1)
    
print sys.argv[0], "using GAMS system directory:", sys.argv[1]
    
gdxHandle = new_gdxHandle_tp()
rc =  gdxCreateD(gdxHandle, sys.argv[1], GMS_SSSIZE)
assert rc[0],rc[1]

print "Using GDX DLL version: " + gdxGetDLLVersion(gdxHandle)[1]
    
assert gdxOpenWrite(gdxHandle, "nikotest.gdx", "nak_test")[0]
assert gdxDataWriteStrStart(gdxHandle, "TimeIdx", "Time data", 1, GMS_DT_SET , 0)

values = doubleArray(GMS_VAL_MAX)

values[GMS_VAL_LEVEL] = 0
gdxDataWriteStr(gdxHandle, ["0"], values)
gdxDataWriteStr(gdxHandle, ["1"], values)

assert gdxDataWriteDone(gdxHandle)
print "Demand data written by nak_test"
    
assert not gdxClose(gdxHandle)
assert gdxFree(gdxHandle)

print "All done nak_test"
        
