import threading
import time
import queue
import requests


class DataProcessor(threading.Thread):
    def __init__(self, server_id, server_ip, servers_list, data_dictionary):
        super().__init__()
        self.server_id = server_id
        self.server_ip = server_ip
        self.servers_list = servers_list
        self.data_dictionary = data_dictionary
        self.queue = queue.Queue()
        self.running = True
        self.message_id = len(self.data_dictionary)

    def run(self):
        while(self.running):
            print("** Data processor Running ****")

            message = self.queue.get()  # Wait if empty
            self.message_id = len(self.data_dictionary)
            message_with_id = {"id": self.message_id,
                               "entry": message}
            # self.data_dictionary[self.message_id] = message

            for i in range(len(self.servers_list)):
                ip = self.servers_list[i]
                # if(ip != self.server_ip):
                self.contact_another_server(
                    ip, "/board", "POST", message_with_id)

        print("** Data processor Stopped ****")

    def contact_another_server(self, srv_ip, URI, req="POST", params_dict=None):
        # Try to contact another serverthrough a POST or GET
        # usage: server.contact_another_server("10.1.1.1", "/index", "POST", params_dict)
        success = False
        try:
            if "POST" in req:
                res = requests.post(
                    "http://{}{}".format(srv_ip, URI), data=params_dict)
            elif "GET" in req:
                res = requests.get("http://{}{}".format(srv_ip, URI))
            # result can be accessed res.json()
            if res.status_code == 200:
                success = True
        except Exception as e:
            print("[ERROR] " + str(e))
        return success

    def stop(self):
        self.running = False

    def isRunning(self):
        return self.running

    def pushData(self, data):
        self.queue.put(data)
