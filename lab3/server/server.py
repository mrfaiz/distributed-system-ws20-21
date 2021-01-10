# coding=utf-8
import argparse
import json
import sys
from threading import Lock, Thread
import time
import traceback
import bottle
from bottle import Bottle, request, template, run, static_file
import requests
import random
from distributed_board import DistributedBoard
from server_details import ServerDetails
from vector_clock import VectorClock
from tem_data_queue import TempDataQueue
from data import Data
from action_type import ActionType
from ast import literal_eval
from utility import get_data_from_other_server, is_left_array_equal_or_small_in_every_index, contact_another_server
from json_keys import JsonKeys
from historires import Histories
from history_processor import HistorProcessor
from client_data_processor import ClientDataProcessor
import logging
# ------------------------------------------------------------------------------------------------------


def current_milli_time(): return int(round(time.time() * 1000))
def intRandomNumber(): return random.randint(1, 100)


prapagation_delay = 5  # in second


class Server(Bottle):

    def __init__(self, serverDetails: ServerDetails):
        super(Server, self).__init__()
        self.serverDetails = serverDetails
        self.histories: Histories = Histories()
        self.distributedBoard = DistributedBoard(serverDetails)
        self.vector_clock: VectorClock = VectorClock(serverDetails)
        self.serverDetails.changeServerTitle(self.vector_clock.getAllClocks())
        self.temp_data_queue: TempDataQueue = TempDataQueue()
        self.dataprocessThread: ClientDataProcessor = None
        self.historyprocessor: HistorProcessor = None

        # list all REST URIs
        # if you add new URIs to the server, you need to add them here
        self.route("/", callback=self.index)
        self.get("/board", callback=self.get_board)
        self.post("/", callback=self.post_index)

        # we give access to the templates elements
        self.get("/templates/<filename:path>", callback=self.get_template)
        self.post("/board", callback=self.add_on_board_by_client)
        self.post("/propagated_data", callback=self.propagated_data)
        self.post("/board/<element_id>/",
                  callback=self.modify_delete_by_client)
        self.get("/sync", callback=self.sync)
        self.get("/get_vector_clock", callback=self.get_vector_clock)
        self.init()

    def propagate_to_all_servers(self, URI, req="POST", params_dict=None):
        for srv_ip in self.serverDetails.getServerList():
            if srv_ip != self.serverDetails.getserverIp():  # don't propagate to yourself
                success = contact_another_server(
                    srv_ip, URI, req, params_dict)
                if not success:
                    print("[WARNING ]Could not contact server {}".format(srv_ip))

    def init(self):
        if(self.dataprocessThread == None or not self.dataprocessThread.isRunning()):
            print("+===============start_data_processing_thread=====================")
            self.dataprocessThread = ClientDataProcessor(
                self.serverDetails, self.histories, self.vector_clock, self.temp_data_queue)
            self.dataprocessThread.start()

        self.historyprocessor = HistorProcessor(
            self.histories, self.distributedBoard)
        self.historyprocessor.start()

    # route to ('/')
    def index(self):
        # we must transform the blackboard as a dict for compatiobility reasons
        # board = dict()
        board = self.distributedBoard.get_board_items()
        return template(
            "server/templates/index.tpl",
            board_title="Server {} ({})".format(
                self.serverDetails.getServerId(), self.serverDetails.getServerIp()),
            board_dict=board.items(),
            server_title=self.serverDetails.getServerTitle(),
            members_name_string="Faiz Ahmed & Md Abu Noman Majumdar",
        )

    # get on ('/board')
    def get_board(self):
        # we must transform the blackboard as a dict for compatibility reasons
        # board = dict()
        board = self.distributedBoard.get_board_items()
        return template(
            "server/templates/blackboard.tpl",
            board_title="Server {} ({})".format(
                self.serverDetails.getServerId(), self.serverDetails.getServerIp()),
            server_title=self.serverDetails.getServerTitle(),
            board_dict=board.items(),
        )

    # post on ('/')
    def post_index(self):
        try:
            # we read the POST form, and check for an element called 'entry'
            new_entry = request.forms.get(JsonKeys.ENTRY)

            print("Received: {}".format(new_entry))
        except Exception as ex:
            logging.exception(ex)

    # post on ('/board')
    def add_on_board_by_client(self):
        try:
            text = request.forms.get("entry")
            print("Received ==> {} ".format(text))
            self.vector_clock.increaseSelfClock()
            temp_vc = self.vector_clock.getAllClocks().copy()
            data = Data(text, element_id = "", action_type = ActionType.ADD,
                        server_id = self.serverDetails.server_id, need_to_propagate=True)
            data.set_vector_clock(temp_vc)  

            # Put data in queue to maintain insertion order (FIFO)
            self.temp_data_queue.putData(data)
        except Exception as ex:
            logging.exception(ex)

    # post (/propagated_data)
    def propagated_data(self):
        try:
            element_id: str = request.forms.get(JsonKeys.ELEMENT_ID, type = str)
            vc = [int(clock)
                  for clock in request.forms.getlist(JsonKeys.VECTOR_CLOCK)]
            text = request.forms.get(JsonKeys.ENTRY, type = str)
            action_type: int = request.forms.get(
                JsonKeys.ACTION_TYPE, type=int)
            server_id = request.forms.get(JsonKeys.SERVER_ID, type=int)

            ## VC from another process, so need to update with max and increase the self
            self.vector_clock.update_with_max_and_increase_self(vc)

            print("[proppagated_data]: element_id = {} vc = {}, text = {}, server_id = {}, action_type = {}".format(element_id, vc, text, server_id, action_type))
            data = Data(text, element_id, action_type,
                        server_id=server_id, need_to_propagate=False)
            data.set_vector_clock(vc)
            self.histories.appendHistory(data)
        except Exception as ex:
            logging.exception(ex)

    def modify_delete_by_client(self, element_id):
        try:
            isDelete = request.forms.get(JsonKeys.DELETE, type=int)
            print("e_id {} isDelete {}".format(element_id, isDelete))
            self.vector_clock.increaseSelfClock()
            temp_vc = self.vector_clock.getAllClocks().copy()
            if isDelete == 1:
                data = Data("", element_id, ActionType.DELETE, server_id=self.serverDetails.server_id, need_to_propagate=True)
                data.set_vector_clock(temp_vc)
                self.temp_data_queue.putData(data)
                self.distributedBoard.delete_if_exist(data.element_id)
            else:
                text = request.forms.get(JsonKeys.ENTRY, type=str)
                data = Data(text, element_id, ActionType.UPDATE, server_id=self.serverDetails.server_id, need_to_propagate=True)
                data.set_vector_clock(temp_vc)
                self.temp_data_queue.putData(data)
                self.distributedBoard.update_text_from_borad(data)
        except Exception as ex:
            logging.exception(ex)
    # get "/sync"

    def sync(self):
        return self.distributedBoard.get_board_items()

    # get "/get_vector_clock"
    def get_vector_clock(self):
        return {"vc": self.vector_clock.getAllClocks()}

    def get_template(self, filename):
        return static_file(filename, root="./server/templates/")

# ------------------------------------------------------------------------------------------------------


def main():
    PORT = 80
    parser = argparse.ArgumentParser(
        description="Your own implementation of the distributed blackboard"
    )
    parser.add_argument(
        "--id", nargs="?", dest="id", default=1, type=int, help="This server ID"
    )
    parser.add_argument(
        "--servers",
        nargs="?",
        dest="srv_list",
        default="10.1.0.1,10.1.0.2",
        help="List of all servers present in the network",
    )
    args = parser.parse_args()
    server_id = args.id
    server_ip = "10.1.0.{}".format(server_id)
    servers_list = args.srv_list.split(",")
    # lead?er_ip = servers_list[len(servers_list)-1]
    serverDeails = ServerDetails(server_id, server_ip, "Slave", servers_list,)
    try:
        server = Server(serverDeails)
        bottle.run(server, host=server_ip, port=PORT)
        print("Started ......")
    except Exception as ex:
        logging.exception(ex)


# ------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
