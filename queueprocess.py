import multiprocessing as mp

class QueueProcess(mp.Process):

    def __init__(self, queue):
        mp.Process.__init__(self)
        self.queue = queue

    def send_status(self, status):
        self.queue.put((self.pid, status))

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
