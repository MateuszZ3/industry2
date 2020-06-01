from enums import Operation


HOST = "localhost"
TR_SPEED = 1
OP_DURATIONS = {
    Operation.DRILL: 1000,
    Operation.MILL: 1500
}
RECEIVE_TIMEOUT = 10 * 60 * 1000
