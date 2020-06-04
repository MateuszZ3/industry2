from enums import Operation

# manager/factory jid: {*}@{HOST}
# tr/gom jid: {*_base}{id}@{HOST}
HOST = "localhost"
AGENT_NAMES = {
    "tr_base": "tr-",
    "gom_base": "gom-",
    "manager": "manager",
    "factory": "factory",
}
PASSWORD = "password"
TR_SPEED = 1  # px/s
OP_DURATIONS = {
    Operation.DRILL: 1000,
    Operation.MILL: 1500
}
RECEIVE_TIMEOUT = 15 * 60  # s
MANAGER_LOOP_TIMEOUT = 0.1  # s
AGENT_CREATION_SLEEP = 0.15  # s
TR_TICK_DURATION = 0.1  # s
