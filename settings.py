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
TR_SPEED = 10  # px/s
OP_DURATIONS = {
    Operation.DRILL: 1000,
    Operation.MILL: 1500,
    Operation.FURNACE: 2100,
    Operation.PRINT: 1600,
    Operation.PELLET: 1000,
    Operation.SHAPE: 1100,
    Operation.PRESS: 1700,
    Operation.INJECT: 1500,
    Operation.MOULD: 1800,
    Operation.SHAVE: 1200,
    Operation.CNC: 1900,
    Operation.GRIND: 2000,
    Operation.CUT_GLASS: 1300,
    Operation.LASER_MARK: 1400
}
RECEIVE_TIMEOUT = 15 * 60  # s
MANAGER_LOOP_TIMEOUT = 0.1  # s
AGENT_CREATION_SLEEP = 0.15  # s
TR_TICK_DURATION = 0.1  # s
