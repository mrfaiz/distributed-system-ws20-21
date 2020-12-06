from threading import Lock

class ServerData:
    server_ip = None

    board = dict()  # global board
    board_lock = Lock()  # Used for locking the board

    @classmethod
    def get_board_items(ServerData):
        with ServerData.board_lock:
            board = ServerData.board
            return board

    @classmethod
    def delete_key(ServerData,key):
        print("[DELETE] " + str(key))
        with ServerData.board_lock:
            try:
                del ServerData.board[key]
            except KeyError as ex:
                print("[ERROR] " + str(ex))
            return
    @classmethod
    def get_value(ServerData,key):
        with ServerData.board_lock:
            value = ServerData.board[key]
            return value

    @classmethod
    def insert_or_update_in_board(ServerData, new_content, e_id):
        new_kew = e_id
        with ServerData.board_lock:
            # if len(new_kew.strip()) == 0:
            #     c_time = current_milli_time()
            #     new_kew = (
            #         str(c_time) + "_" + str(e_id)
            #     )  # id = 23423432_1 , (there same data in same mili second in all server, that's why I used _ and server id)
            # ServerData.blackboard.set_content(new_content)
            ServerData.board[new_kew] = new_content
        return new_kew
