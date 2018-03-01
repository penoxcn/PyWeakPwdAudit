#!/usr/bin/env python
# coding=utf-8

import re
import itelnet
import logging
from xutils import encode_utf8

TELNET_CONN_TIMEOUT = 6.0
TELNET_USER_TIMEOUT = 6.0
TELNET_AUTH_TIMEOUT = 12.0

class TelnetAuth:
    def __init__(self, (host,port)):
        self.addr = (host, port)
        
    def login(self, username, password, timeout=TELNET_CONN_TIMEOUT):
        conn_ok, auth_ok, username_ok, no_username, no_password, banner = False,False,False, False, False, ''
        connection = None
        try:
            connection = itelnet.Telnet(self.addr[0], self.addr[1], timeout = timeout)
            text = connection.read_some(timeout=TELNET_USER_TIMEOUT)
            ftype,banner = connection.parse_banner(text)
            if ftype=='SHELL' or ftype=='LOGOK':
                conn_ok,auth_ok,username_ok,no_username,no_password= True,True,True,True,True
                logging.getLogger().warn('FOUND:1 <EMPTY> %s:%d %r' % (self.addr[0], self.addr[1], banner))
            elif ftype=='IGNORE' or ftype=='OTHER':
                logging.getLogger().info('IGNORE:2 %s:%d [EOF:%s] %r' % (self.addr[0], self.addr[1], str(connection.iseof()), banner))
            elif ftype=='LOGIN':
                conn_ok = True
            elif ftype=='PASSWORD':
                conn_ok = True
                no_username = True
                username_ok = True
                logging.getLogger().info('NOUSER:3 %s:%d' % (self.addr[0], self.addr[1]))
        except:
            logging.getLogger().info('ECON:4 %s:%d X' % (self.addr[0], self.addr[1]))
        if not conn_ok or connection.iseof() or auth_ok:
            if connection:
                connection.close()
            return conn_ok, auth_ok, username_ok, no_username, no_password, banner
        
        #need username
        if not no_username:
            try:
                connection.write(username+'\r\n')
                text = connection.read_some(timeout=TELNET_USER_TIMEOUT)
                ftype, banner = connection.parse_auth(text)
                if ftype=='PASSWORD':
                    username_ok = True
                elif ftype=='SHELL' or ftype=='LOGOK':
                    username_ok = True
                    auth_ok = True
                    no_password = True
                    logging.getLogger().warn('FOUND:5 %s:<EMPTY> %s:%d %r' % (username, self.addr[0], self.addr[1], banner))
                elif ftype=='OTHER':
                    if banner.strip()==username:
                        username_ok = True
                    else:
                        conn_ok = False
                        logging.getLogger().info('IGNORE:6 %s:%d %r' % (self.addr[0], self.addr[1], banner))
                else:#LOGIN
                    username_ok = False
                    logging.getLogger().info('EUSER:7 %s:%d USER:%s %r' % (self.addr[0], self.addr[1], username, banner))
            except Exception as e:
                conn_ok = False
                logging.getLogger().info('ECON:8 %s:%d %s' % (self.addr[0], self.addr[1], str(e)))
            if not conn_ok or connection.iseof() or not username_ok:
                connection.close()
                return conn_ok, auth_ok, username_ok, no_username, no_password, banner
            
        #username_ok
        if username_ok:
            try:
                connection.write(password+'\r\n')
                text = connection.read_some(timeout=TELNET_AUTH_TIMEOUT)
                ftype,banner = connection.parse_auth(text)
                if ftype=='SHELL' or ftype=='LOGOK':
                    auth_ok = True
                    logging.getLogger().warn('FOUND:9 %s:%s %s:%d %r' % ('<EMPTY>' if no_username else username, password, self.addr[0], self.addr[1], banner))
                elif ftype=='OTHER' and banner.strip() and banner.strip()!=username:
                    conn_ok = False
                    logging.getLogger().info('EPSWD:10 %s:%s %s:%d %r' % ('<EMPTY>' if no_username else username, password, self.addr[0], self.addr[1], banner))
                elif ftype=='IGNORE':
                    logging.getLogger().info('IGNORE:11 %s:%d %r' % (self.addr[0], self.addr[1], banner))
                    conn_ok = False
                else:#LOGIN, FAIL
                    auth_ok = False
            except Exception as e:
                conn_ok = False
                logging.getLogger().info('ECON:12 %s:%d %s' % (self.addr[0], self.addr[1], str(e)))
                
        if connection:
            connection.close()
        del connection
        return conn_ok, auth_ok, username_ok, no_username, no_password, banner


class TelnetBruteTester:
    def __init__(self, userdict, passwords = None):
        self.userdict = userdict
        self.passwords = passwords
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = TelnetAuth( (host,port) )
        username = 'ANYUser'
        password = 'ANYPswd'
        conn_ok, auth_ok, username_ok, no_username, no_password, banner = auth.login(username, password)
        if not conn_ok:
            return rs
        
        if auth_ok:
            rs.append([host, port, 'TELNET', '<EMPTY>' if no_username else username, '<EMPTY>' if no_password else password, encode_utf8(banner)])
            return rs
    
        if no_username:
            for password in self.passwords:
                conn_ok, auth_ok, username_ok, no_username, no_password, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if auth_ok:
                    rs.append([host, port, 'TELNET', '<EMPTY>' if no_username else username, '<EMPTY>' if no_password else password, encode_utf8(banner)])
                    if no_username:
                        return rs
                    break #next user
            if not rs:
                logging.getLogger().info('SAFE %s:%d'%(host, port)) 
            return rs
        
        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok, auth_ok, username_ok, no_username, no_password, banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if auth_ok:
                    rs.append([host, port, 'TELNET', '<EMPTY>' if no_username else username, '<EMPTY>' if no_password else password, encode_utf8(banner)])
                    if no_username:
                        return rs
                    break #next user
                if not username_ok:
                    break #next user
        if not rs:
           logging.getLogger().info('SAFE %s:%d'%(host, port)) 
        return rs

if __name__=='__main__':
    import sys
    import xutils
    host,port = sys.argv[1],int(sys.argv[2])
    
    userdict = dict()
    passwords = set()
    for ln in open(sys.argv[3]):
        fs = ln.strip().split(':',1)
        if len(fs)!=2:
            continue
        username = fs[0]
        password = fs[1]
        passwords.add(password)
        if username not in userdict:
            userdict[username] = set()
        userdict[username].add(password)
    logger = xutils.initLogger(sys.argv[4])
    tester = TelnetBruteTester(userdict, passwords)
    rs = tester.test( (host,port) )
    print rs
    

