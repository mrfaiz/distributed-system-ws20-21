import threading
import time
import queue
import requests
import json
# from server_data import ServerData
from server_details import ServerDetails
from distributed_board import DistributedBoard
from vector_clock import VectorClock
from tem_data_queue import TempDataQueue
from data import Data
from action_type import ActionType
from utility import get_data_from_other_server, is_left_array_equal_or_small_in_every_index, contact_another_server, generate_unique_id
from json_keys import JsonKeys
from historires import Histories
import logging

class ClientDataProcessor(threading.Thread):
    def __init__(self, server_details: ServerDetails, histories: Histories, vector_clock: VectorClock, temp_data_queue: TempDataQueue):
        super().__init__()
        self.server_details = server_details
        self.histories = histories
        self.running = True
        self.vector_clock = vector_clock
        self.temp_data_queue = temp_data_queue
        self.message_counter = 0

    def run(self):
        print("Data processor started")
        while(self.running):
            try:
                data: Data = self.temp_data_queue.queue.get()  # Wait if empty
                print("[ClientDataProcessor]: text = {}, element_id = {}, action_type = {}".format(
                    data.text, data.element_id, data.action_type))
                # It's mandatory to create an unique id for each message while adding new message
                if(data.action_type == ActionType.ADD): 
                    self.message_counter += 1
                    data.element_id = generate_unique_id(self.server_details.getServerId(), self.message_counter)

                if(data.text != None and len(data.element_id) > 0):
                    message_with_id = {
                        JsonKeys.ELEMENT_ID: data.element_id,
                        JsonKeys.ENTRY: data.text,
                        JsonKeys.VECTOR_CLOCK: data.vector_clock,
                        JsonKeys.ACTION_TYPE: int(data.action_type),
                        JsonKeys.SERVER_ID: self.server_details.server_id
                    }
                    self.histories.appendHistory(data)
                    print("[ClientDataProcessor: json to send] : {}".format(message_with_id))
                    self.propagate_to_all_servers("/propagated_data", "POST", message_with_id)                          
                else:
                    print("[ClientDataProcessor: Error] text = {}, element_id = {}, action_type = {}".format(data.text, data.element_id, data.action_type))

            except Exception as identifier:
                logging.exception(identifier)
        print("** Data processor Stopped ****")

    def stop(self):
        self.running = False

    def isRunning(self):
        return self.running
    

    def propagate_to_all_servers(self, URI, req="POST", params_dict=None):
        for srv_ip in self.server_details.getServerList():
            if srv_ip != self.server_details.getServerIp():  # don't propagate to yourself
                success = contact_another_server(
                    srv_ip, URI, req, params_dict)
                if not success:
                    print("[ClientDataProcessor: propagate_to_all_servers : WARNING ] {}".format(srv_ip))