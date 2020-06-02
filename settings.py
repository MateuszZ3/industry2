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
TR_SPEED = 1
OP_DURATIONS = {
    Operation.DRILL: 1000,
    Operation.MILL : 1500
}
RECEIVE_TIMEOUT = 10 * 60 * 1000  # ms
MANAGER_LOOP_TIMEOUT = 10  # s
