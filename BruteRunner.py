#!/usr/bin/env python
# coding=utf-8

import os
import random
import logging
import time

import xutils
from BruteThread import BruteWorker

#ds: DataStorage
class BruteRunner(BruteWorker):
    def __init__(self, ds):
        BruteWorker.__init__(self, ds)
        
    def workerRun(self, args):
        tester = args['constructor'](args['userdict'], args['passwords'])
        if args['id']<3 or args['id']>args['nworker']-2:
            logging.getLogger().info('BruteRunner: pid=%d thread=%d started'
                                     % (os.getpid(),args['id']))
        taskcount = 0
        while not args['quit']():
            try:
                task = args['fetch'](timeout=3)
                if task is None:
                    continue
                taskcount += 1
                
                rs = tester.test(task)
                if rs:
                    args['save'](rs)
            except Exception as e:
                logging.getLogger().warn('BruteRunner: pid=%d thread=%d %s' % (os.getpid(),args['id'], str(e)))
                
        if args['id']<3 or args['id']>args['nworker']-2:
            logging.getLogger().info('BruteRunner: pid=%d thread=%d tasks=%d finished'
                                     % (os.getpid(),args['id'],taskcount))
            

class BruteStorage:
    def __init__(self, ds):
        #ds object has a member call Save who saves data to file or database...
        self.ds = ds
        
    def close(self):
        #TODO:
        #close files, database connections, ...
        pass
        
    def getTargets(self):
        #TODO:
        #you can load targets from file, or database, wherever you like...
        data = [('1.1.1.1',23),
                ('2.2.2.2',23),
                ('3.3.3.3',445),
                ('192.168.1.1',445),]
        return data
    
    def escape(self, s):
        chars = ['\\','\'','\"']
        for c in chars:
            s = s.replace(c,'\\'+c)
        return s
       
    def saveResult(self, rs):
        if not rs:
            return
        #[(ip,port,service,username,password,output),]
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        for r in rs:
            d = [
                     r[0], #ip
                     str(r[1]), #port
                     r[2], #service 
                     r[3], #username
                     self.escape(r[4]), #password
                     self.escape(r[5]), #output
                     now,# timestamp
                     ]
            #TODO:
            #call self.ds.Save To save results to file, or save to database, ...
            self.ds.Save(d)

    
class Bruter:
    def __init__(self, constructor):
        self.constructor = constructor
        self.targets = None
        self.userdict = None
        self.pid = 0
        
    def loadUserDict(self, fpath):
        userdict = dict()
        try:
            for ln in open(fpath):
                fs = ln.strip().split(':',1)
                if len(fs)!=2:
                    continue
                username = fs[0]
                password = fs[1]
                if username not in userdict:
                    userdict[username] = set()
                userdict[username].add(password)
        except Exception as e:
            pass
        return userdict

    #config holds some key parameters for program, like database config, file path ...
    def prepare(self, config):
        retval = True
        logging.getLogger().info('Bruter.prepare: begin.')

        #TODO: Please implement your DataBaseStorage
        ### TO BE COMPLETED ###
        dbs = DataBaseStorage(config)
        store = BruteStorage(dbs)
        
        userdict = self.loadUserDict(config['userdict'])
        self.userdict = userdict
        self.passwords = set()
        for u in userdict:
            self.passwords |= userdict[u]
        
        self.targets = store.getTargets()
    
        if len(self.userdict)==0 or len(self.targets)==0:
            logging.getLogger().warn('Bruter.prepare: %d userdict, %d targets. end.' % (len(self.userdict), len(self.targets)))
            retval = False

        logging.getLogger().info('Bruter.prepare: %d userdict, %d targets. ready.' % (len(self.userdict), len(self.targets)))

        ##because we are using Multi Processing, so we must close DataStorage before contiue.
        dbs.close()
        return retval

    def fork(self,nprocess):
        idx = 0
        if nprocess>=1:
            idx = -1
            for i in range(nprocess):
                pid = os.fork()
                if pid == 0: #child
                    idx = i
                    #going to background
                    os.chdir('/')
                    os.setsid()
                    os.umask(0)
                    break
                else: #parent
                    continue
            if pid != 0: #parent
                logging.getLogger().info('Bruter.fork: fork done.')
                idx = -1
        return idx
            
    def start(self, config):
        if not self.prepare(config):
            return

        #multiprocessing
        nprocess = int(config['processes'])
        idx = self.fork(nprocess)
        xutils.closeLogger()
        if idx==-1: #parent
            return

        self.pid = os.getpid()
        
        self.logger = xutils.initLogger(config['logfile'])
        num = len(self.targets)/nprocess
        if num*nprocess<len(self.targets):
            num += 1
        self.targets = self.targets[num*idx : num*idx+num]

        #TODO:
        #Please implement your DataBaseStorage object
        dbs = DataBaseStorage(config)
        store = BruteStorage(dbs)
        bruter = BruteRunner(store)

        nworker = int(config['threads'])
        kargs = {'constructor':self.constructor, 'userdict':self.userdict, 'passwords':self.passwords}
        bruter.start(nworker, kargs)

        maxruntime = float(config['maxruntime'])
        starttime = time.time()
        endtime = starttime + maxruntime
        
        for task in self.targets:
            bruter.putTask(task)
       
        taskleft = bruter.getTaskCount()
        while time.time()<endtime and taskleft>0:
            time.sleep(5)
            taskleft = bruter.getTaskCount()
        bruter.signal()
        time.sleep(5)
        bruter.stop(60)
        store.close()
        dbs.close()
        logging.getLogger().info('Bruter.start: pid:%d, runtime:%.2fS. done.' 
                        % (self.pid, time.time()-starttime))

if __name__=='__main__':
    pass
