#!/usr/bin/env python
# coding=utf-8

import MySQLdb
import logging
from xutils import encode_utf8

LOGIN_TIMEOUT = 12
    
class MysqlAuth:
    def __init__(self, (host,port)):
        self.addr = (host, port)
        
    def login(self, username, password, timeout=LOGIN_TIMEOUT):
        conn_ok, auth_ok, anonymous, banner = False, False, False, ''
        connection = None
        try:
            connection = MySQLdb.connect(host=self.addr[0],port=self.addr[1],
                                         user=username,passwd=password,
                                         db='mysql',connect_timeout=LOGIN_TIMEOUT)
            conn_ok = True
            auth_ok = True
            anonymous = False
            cursor = connection.cursor()
            cursor.execute('SELECT @@VERSION')
            row = cursor.fetchone()
            banner = str(row[0])
            
            cursor.execute('SELECT CURRENT_USER()')
            row = cursor.fetchone()
    
            if str(row[0])[0]=='@':
                anonymous = True
            else:
                logging.getLogger().warn('FOUND %s:%s@%s:%d<OK>'%(username, password, self.addr[0], self.addr[1]))
            cursor.close()
            
        except Exception as e:
            es = str(e)
            msg = es[0:6].strip('(').strip(')').strip(',')
            #Error: 1044 SQLSTATE: 42000 (ER_DBACCESS_DENIED_ERROR)
            #Error: 1045 SQLSTATE: 28000 (ER_ACCESS_DENIED_ERROR)
            #if es.find('(1045,')>=0 or es.find('(1044,')>=0:
            if msg=='1044' or msg=='1045':
                conn_ok = True
            else:
                logging.getLogger().info('ECON:1 %s:%d X %s' % (self.addr[0], self.addr[1], msg))
        if connection:
            connection.close()
        del connection
        return conn_ok, auth_ok, anonymous, banner


class MysqlBruteTester:
    def __init__(self, userdict, passwords=None):
        self.userdict = userdict
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = MysqlAuth( (host, port) )
        anony = False
        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok, auth_ok, anonymous, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if not auth_ok:
                    continue
                if anonymous:
                    if not anony:
                        anony = True
                        logging.getLogger().warn('FOUND anonymous@%s:%d<OK>'%(host, port))
                        rs.append([host, port, 'MYSQL', '<ANY>', '<ANY>', encode_utf8(banner)])
                    continue
                rs.append([host, port, 'MYSQL', username, password, encode_utf8(banner)])
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
    tester = MysqlBruteTester(userdict)
    rs = tester.test( (host,port) )
    print rs
