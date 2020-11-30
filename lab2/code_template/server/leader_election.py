#!/usr/bin/python3
import socket
import threading
import time
import random
import requests


class Election(threading.Thread):
    def __init__(self, server_ip, server_id, server_list):
        super().__init__()
        self.server_id = server_id
        self.server_ip = server_ip
        self.server_list = server_list
        # self.leader_ip = leader_ip

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

    def run(self):
        # while(True):
        print("============== Running Election Thread===========================")
        time.sleep(1)
        print(self.server_list)
        # print("Leader IP : ",self.leader_ip)
        elected = True
        no_of_servers = len(self.server_list)
        if(no_of_servers != self.server_id):  ## started from last index
            # for i in range(self.server_id-1, len(self.server_list)-1):
            for i in range(no_of_servers-1, self.server_id, -1):
                ip = self.server_list[i]
                print("send election to :"+ip)
                messge = {"l_id": self.server_id,
                          "l_ip": self.server_ip, "entry": "test"}
                success = self.contact_another_server(
                    ip, "/election", "POST", messge)
                if(success):
                    elected = False
                    break
        if(elected):
            print("=================I am the Coordinator=========== \nid: {} , ip: {}".format(self.server_id,self.server_ip))
            for i in range(len(self.server_list)):
                ip = self.server_list[i]
                if self.server_ip != ip:
                    messge = {"l_id": self.server_id,
                              "l_ip": self.server_ip, "entry": "test"}
                    success = self.contact_another_server(
                        ip, "/leader", "POST", messge)
                    print(" Leader selected sent =>{} , response : {}".format(
                        ip, success))

    def gerServerList(self):
        return self.server_list