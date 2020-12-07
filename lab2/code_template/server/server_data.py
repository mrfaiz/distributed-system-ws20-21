from threading import Lock

class ServerData:
    leader_ip = None

    board = dict()  # global board
    board_lock = Lock()  # Used for locking the board