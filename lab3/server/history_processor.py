from threading import Lock, Thread
from data import Data
from distributed_board import DistributedBoard
from historires import Histories
from utility import currrent_time_secs, sleep, print_stack_trace
from action_type import ActionType


class HistorProcessor(Thread):

    def __init__(self, histories: Histories, distributed_board: DistributedBoard):
        super().__init__()
        self.histories = histories
        self.distributed_board = distributed_board
        # self.time_last_client_message: int = currrent_time_secs()
        self.lock = Lock()
        self.wait_counter = 0
        self.total_processed_history = 0

    def run(self):
        print("[HistoryProcessor]: started")
        while(True):
            try:
                sleep(5)
                current_number_of_history = len(
                    self.histories.get_history_list())
                # check last message time with current time
                diff_in_sec = currrent_time_secs() - self.histories.get_latest_history_entry_time()

                if current_number_of_history == self.total_processed_history:  # No new data
                    # print("[HistorProcessor] running : No new data since {} secs".format(
                    #     diff_in_sec))
                    continue

                if diff_in_sec <= 15:
                    print("[HistorProcessor] new data found, waiting {} secs for more data".format(
                        diff_in_sec))
                    self.wait_counter += self.wait_counter
                    # Wait maximum 100 sec, If data is continously comming , time diff always will be less then 20 sec
                    if self.wait_counter < 5:
                        continue

                # Reset wait count
                self.wait_counter = 0

                # Load the temp history into distributed board
                # My Choice: Casual Ordering
                # VC from server1 = [1,0,0,1], VC from server2 = [1,0,0,0], So server2 -> server1 (server2 precced server1)
                # VC from server1 = [1,0,0,1], VC from server2 = [1,0,1,0], same oder, in that case odered by server ID ascending
                #    server1 precced server2

                total_data_to_process = current_number_of_history - self.total_processed_history
                if total_data_to_process > 0:
                    print("[HistorProcessor]: Processing started, #data to process: {} ".format(
                        total_data_to_process))

                    temp_history: [Data] = self.histories.get_history_list(
                    )[self.total_processed_history:current_number_of_history].copy()
                    # self.histories.clearHistory()
                    self.total_processed_history = current_number_of_history
                    temp_history.sort(key=lambda log: (
                        log.vector_sum, log.server_id))

                    for data in temp_history:
                        print("[HistorProcessor]: processing ,text = {} , vc = {} , server_id = {}, action_type = {}".format(
                            data.text, data.vector_clock, data.server_id, data.action_type))
                        if data.action_type == ActionType.ADD:
                            self.distributed_board.add_on_board(data)
                        elif data.action_type == ActionType.UPDATE:
                            ret = self.distributed_board.update_text_from_borad(
                                data)
                            if not ret:
                                print("[HistorProcessor]: update failed, element_id = {}".format(
                                    data.element_id))
                        elif data.action_type == ActionType.DELETE:
                            self.distributed_board.delete_if_exist(
                                data.element_id)

                    # For Huge amount of data the following process is not Appropriate, Because I am processing all the data every time

                    # self.total_processed_history = current_number_of_history
                    # self.histories.get_history_list().sort(
                    #     key=lambda log: (log.vector_sum, log.server_id))
                    # temp_dictionary = dict()
                    # for data in self.histories.get_history_list():
                    #     print("[HistorProcessor]: processing ,text = {} , vc = {} , server_id = {}, action_type = {}".format(
                    #         data.text, data.vector_clock, data.server_id, data.action_type))
                    #     if data.action_type == ActionType.ADD:
                    #         temp_dictionary[data.element_id] = data
                    #     elif data.action_type == ActionType.UPDATE:
                    #         if data.element_id in temp_dictionary:
                    #             temp_dictionary[data.element_id].text = data.text
                    #     elif data.action_type == ActionType.DELETE:
                    #         if data.element_id in temp_dictionary:
                    #             del temp_dictionary[data.element_id]

                    # self.distributed_board.board_data = temp_dictionary
                else:
                    print("[HistorProcessor]: No data yet")
            except Exception as ex:
                print_stack_trace(ex)
            finally:
                pass
