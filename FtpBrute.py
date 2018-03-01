#!/usr/bin/env python
# coding=utf-8

import re
import logging
import ftplib
from xutils import encode_utf8

FTP_CONN_TIMEOUT = 8

class FtpAuth:
    def __init__(self, (host,port)):
        self.addr = (host, port)

    def login(self, username, password, timeout=FTP_CONN_TIMEOUT):
        conn_ok, auth_ok, banner = False, False, ''
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.addr[0], self.addr[1], timeout = timeout)
            conn_ok = True
            ftp.login(username, password)
            auth_ok = True
            logging.getLogger().warn('FOUND %s:%s@%s:%d<OK>'%(username, password, self.addr[0], self.addr[1]))
            banner = ftp.getwelcome()
            ftp.close()
        except Exception as e:
            if not conn_ok:
                logging.getLogger().info('ECON:1 %s:%d X' % (self.addr[0], self.addr[1]))
            pass
        del ftp
        return conn_ok, auth_ok, banner


class FtpBruteTester:
    def __init__(self, userdict, passwords=None):
        self.userdict = userdict
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = FtpAuth( (host,port) )
        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok, auth_ok, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if not auth_ok:
                    continue
                rs.append([host, port, 'FTP', username, password, encode_utf8(banner)])
                break
        if not rs:
           logging.getLogger().info('SAFE %s:%d'%(host, port)) 
        return rs

if __name__=='__main__':
    import sys
    import xutils
    host,port = sys.argv[1],int(sys.argv[2])
    
    userdict = dict()
    for ln in open(sys.argv[3]):
        fs = ln.strip().split(':',1)
        if len(fs)!=2:
            continue
        username = fs[0]
        password = fs[1]
        if username not in userdict:
            userdict[username] = set()
        userdict[username].add(password)
    logger = xutils.initLogger(sys.argv[4])
    tester = FtpBruteTester(userdict)
    rs = tester.test( (host,port) )
    print rs
