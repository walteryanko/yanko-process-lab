from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DT=.015
N=57
M=6
T_LIMIT=(180-32)/1.8+273.15
T_DESIGN=T_LIMIT-2.0
CP_DELTA=(35+18-46)*4.1868
SEEDS=list(range(100200,100220))
SENSOR_STD=np.array([1.385,1.062])/1.8
SENSOR_BOUND=3*SENSOR_STD
RATE_BOUNDS=(.60,1.50)
UA_BOUNDS=(.65,1.30)
