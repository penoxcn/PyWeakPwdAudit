#!/usr/bin/env python
# coding=utf-8

import os
import logging
import threading
import time
from Queue import Queue,Empty

class BruteWorker:
    
    def workerRun(self, args):
        return True
    
    def __init__(self, ds):
        self.done = False
        self.workers = []
        self.queue = Queue()
        self.ds = ds
        self.lock = threading.RLock()
        self.pid = os.getpid()

    def start(self, n, kargs={}):
        logging.getLogger().info('Scanner.start:#%d, %d threads' % (self.pid, n))
        self.startWorkers(n, kargs)

    def getQuit(self):
        return self.done

    def putTask(self, task):
        self.queue.put(task)
        return True

    def getTask(self, timeout = 3):
        try:
            return self.queue.get(True, timeout)
        except Empty:
            return None
        
    def getTaskCount(self):
        return self.queue.qsize()

    def signal(self):
        self.done = True
        #logging.getLogger().info('Scanner.signal:#%d, ok.'% (self.pid))
        
    def stop(self, timeout=60.0):
        logging.getLogger().info('Scanner.stop:#%d, begin.'% (self.pid))
        self.done = True
        done = 0
        endtime = time.time() + timeout
        nworker = len(self.workers)
        while done<nworker and time.time()<endtime:
            idx = 0
            while idx<nworker:
                if self.workers[idx] is not None:
                    self.workers[idx].join(0.05)
                    if not self.workers[idx].isAlive():
                        done += 1
                        self.workers[idx] = None
                idx += 1
            time.sleep(1.0)
                
        logging.getLogger().info('Scanner.stop:#%d, %d workers done.' % (self.pid, done))
        left = len(self.workers) - done
        return left
        
    def saveResult(self, rs):
        self.lock.acquire()
        try:
            self.ds.saveResult(rs)
        except Exception as e:
            logging.getLogger().warn('Scanner.saveResult:#%d, %s'%(self.pid, str(e)))
        self.lock.release()
  
    def startWorkers(self, n, kargs):
        for i in range(n):
            args = {'id':i+1, 'nworker':n, 'fetch':self.getTask, 'quit':self.getQuit, 'save':self.saveResult}
            for key in kargs:
                args[key] = kargs[key]
            thread = threading.Thread(target=self.workerRun,args=(args,))
            self.workers.append(thread)
            thread.start()
            

