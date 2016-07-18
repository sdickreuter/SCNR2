import multiprocessing as mp

class StatusProcess(mp.Process):

    def __init__(self, status_queue, command_queue):
        mp.Process.__init__(self)
        self.status_queue = status_queue
        self.command_queue = command_queue

    def send_status(self, status):
        self.status_queue.put((self.pid,status))

    def saferun(self):
        # Overwrite this method
        pass

    def run(self):
        try:
            self.saferun()
        except Exception as e:
            self.send_status(e)
            self.terminate()
            raise e
        return
