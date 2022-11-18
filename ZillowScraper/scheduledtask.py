from threading import Timer

class scheduledtask:

    def __init__(self, interval, function):
        self.is_active = False
        self.timer = None
        self.interval = interval
        self.function = function

    def re_run(self):
        self.function()
        self.is_active = False
        del self.timer
        self.start()

    def start(self):
        if not self.is_active:
            self.timer = Timer(self.interval, self.re_run)
            self.timer.name = "me"
            self.timer.setDaemon(True)
            self.is_active = True
            self.timer.start()

    def stop(self):
        if self.is_active:
            self.timer.cancel()
            self.is_active = False


if __name__ == "__main__":

   
    def dummy():
        print("dummy")

    task1 = scheduledtask(5, dummy)

    