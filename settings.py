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
OP_DURATIONS = {  # s
    Operation.DRILL: 1.,
    Operation.MILL: 1.5,
    Operation.FURNACE: 2.1,
    Operation.PRINT: 1.6,
    Operation.PELLET: 1.,
    Operation.SHAPE: 1.1,
    Operation.PRESS: 1.7,
    Operation.INJECT: 1.5,
    Operation.MOULD: 1.8,
    Operation.SHAVE: 1.2,
    Operation.CNC: 1.9,
    Operation.GRIND: 2.,
    Operation.CUT_GLASS: 1.3,
    Operation.LASER_MARK: 1.4,
}
RECEIVE_TIMEOUT = 15 * 60  # s
MANAGER_LOOP_TIMEOUT = 0.1  # s
AGENT_CREATION_SLEEP = 0.1  # s
TR_TICK_DURATION = 0.1  # s
TR_DECIDE_TIMEOUT = 1  # s

TR_POSITION_UPDATE_PERIOD = 0.25  # s
TR_LIST_UPDATE_PERIOD = 1.0  # s

ZOOM_MIN = 0.5
ZOOM_MAX = 5.0
ZOOM_DEFAULT = 2.5
SELECT_RADIUS = 10  # px with zoom=1.0
