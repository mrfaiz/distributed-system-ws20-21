import threading

class DatSynchronizer(threading.Thread):

    def __init__(self, server_details):
        super().__init__()
        self.server_details = server_details
        self.server_id_to_communicate = None