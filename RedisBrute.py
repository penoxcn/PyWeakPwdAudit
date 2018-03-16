#!/usr/bin/env python
# coding=utf-8
# please see: https://pypi.python.org/pypi/redis/
import redis
import logging
from xapps.xapp import encode_utf8

LOGIN_TIMEOUT = 12
      
class RedisAuth:
    def __init__(self, (host,port)):
        self.addr = (host, port)

    #redis don't need an username,just a password called AUTH
    def login(self, username='', password='', timeout=LOGIN_TIMEOUT):
        conn_ok, auth_ok, banner = False, False, ''
        connection = None
        try:
            connection = redis.StrictRedis(host=self.addr[0],port=self.addr[1],
                                         password=password,
                                         db=0,socket_connect_timeout=LOGIN_TIMEOUT)
            conn_ok = True
            auth_ok = True
            info = connection.info()
            banner = str(info)
            logging.getLogger().warn('FOUND %s:%s@%s:%d<OK>'%(username, password, self.addr[0], self.addr[1]))
        except Exception as e:
            es = str(e)
            if es.find('Password')>=0:
                conn_ok = True
            else:
                conn_ok = False
                logging.getLogger().info('ERR:1 %s:%d %s' % (self.addr[0], self.addr[1], es))
        del connection
        return conn_ok, auth_ok, banner


class RedisBruteTester:
    def __init__(self, userdict, passwords=None):
        self.userdict = userdict
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = RedisAuth( (host, port) )
        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok, auth_ok, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if not auth_ok:
                    continue
                rs.append([host, port, 'REDIS', username, password, encode_utf8(banner)])
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
    tester = RedisBruteTester(userdict)
    rs = tester.test( (host,port) )
    print rs
    
