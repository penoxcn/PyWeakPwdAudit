#!/usr/bin/env python
# coding=utf-8

import cx_Oracle
import logging
from xutils import encode_utf8

LOGIN_TIMEOUT = 12
    
class OracleAuth:
    def __init__(self, (host,port)):
        self.addr = (host, port)
        
    def login(self, username, password, timeout=LOGIN_TIMEOUT):
        conn_ok, auth_ok, user_ok, banner = False, False, True, ''
        connection = None
        inst = 'orcl'
        try:
            connstr = '%s/%s@%s/%s' % (username,password,self.addr[0],inst)
            if username.lower()=='sys':
                connection = cx_Oracle.connect(connstr,mode=cx_Oracle.SYSDBA)
            else:
                connection = cx_Oracle.connect(connstr)
            conn_ok = True
            auth_ok = True
            banner = str(connection.version)
            logging.getLogger().warn('FOUND %s:%s@%s:%d<OK>'%(username, password, self.addr[0], self.addr[1]))
        except Exception as e:
            es = str(e).strip()
            auth_ok = False
            if es.find(' timeout ')>=0 or es.find('lost contact')>=0 or es.find('connection closed')>=0:
                conn_ok = False
            elif es.find('ORA-12514:')>=0 or es.find('ORA-12154')>=0: #ORA-12514: sid is unknown
                conn_ok = False             
            elif es.find('ORA-01017:')>=0: #ORA-01017 -> invalid user/password
                conn_ok = True
            elif es.find('ORA-28000:')>=0: #user locked
                conn_ok = True
                user_ok = False
                logging.getLogger().warn('LOCKED %s:%s@%s:%d<LOCKED>'%(username, password, self.addr[0], self.addr[1]))
            elif es.find('ORA-28001:')>=0: #password expired
                conn_ok = True
                auth_ok = True
                logging.getLogger().warn('FOUND %s:%s@%s:%d<EXPIRED>'%(username, password, self.addr[0], self.addr[1]))
            else:
                conn_ok = False
                logging.getLogger().info('ECON:1 %s:%d X %s' % (self.addr[0], self.addr[1], es))
        if connection:
            connection.close()
        del connection
        return conn_ok, auth_ok, user_ok, banner


class OracleBruteTester:
    def __init__(self, userdict, passwords=None):
        self.userdict = userdict
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = OracleAuth( (host, port) )

        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok, auth_ok, user_ok, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if not user_ok:
                    break
                if not auth_ok:
                    continue
                rs.append([host, port, 'ORACLE', username, password, encode_utf8(banner)])
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
    tester = OracleBruteTester(userdict)
    rs = tester.test( (host,port) )
    print rs
