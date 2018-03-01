#!/usr/bin/env python
# coding=utf-8

import os
import cmd
import time
import ntpath
import binascii
import logging
from xutils import encode_utf8
from impacket.nmb import SMB_SESSION_PORT,NETBIOS_SESSION_PORT
from impacket.smbconnection import *

SMB_TIMEOUT = 8
          
class SmbAuth:
    def __init__(self, (host, port)):
        self.addr = (host, port)
        
    def run(self):
        return self.login()
    
    def geterr(self,es):
        idx1 = es.find('STATUS_')
        if idx1==-1:
            return es
        idx2 = es.find('(',idx1)
        return es[idx1:idx2]
        
    def login(self, username, password):
        smbConnection = None
        conn_ok = False
        auth_ok = False
        user_ok = True
        banner = None
        try:
            if self.addr[1]==SMB_SESSION_PORT:
                smbConnection = SMBConnection(remoteName=self.addr[0], remoteHost=self.addr[0], sess_port=SMB_SESSION_PORT, timeout=SMB_TIMEOUT)
            elif self.addr[1]==NETBIOS_SESSION_PORT:
                smbConnection = SMBConnection(remoteName='*SMBSERVER', remoteHost=self.addr[0], sess_port=NETBIOS_SESSION_PORT, timeout=SMB_TIMEOUT)
            else:
                return conn_ok,user_ok,auth_ok,banner
        except Exception as e:
            logging.getLogger().info( 'ECON:1 %s:%s X' % (self.addr[0], self.addr[1]) )
            return conn_ok,user_ok,auth_ok,banner
        
        conn_ok = True
        try:
            smbConnection.login(username, password, '', '', '')
            isGuest = smbConnection.isGuestSession()
            tid = smbConnection.connectTree('ADMIN$')
            pwd = ntpath.join('\\','*')
            pwd = string.replace(pwd,'/','\\')
            pwd = ntpath.normpath(pwd)
            files = smbConnection.listPath('ADMIN$', pwd)
            banner = ''
            for f in files[0:10]:
                banner+='%crw-rw-rw- %10d  %s %s\n' % (
                'd' if f.is_directory() > 0 else '-', f.get_filesize(), time.ctime(float(f.get_mtime_epoch())),f.get_longname())
            if not isGuest:
                auth_ok = True
                logging.getLogger().warn('FOUND: %s:%s @%s:%d<OK>' %(username, password, self.addr[0],self.addr[1]))
        except Exception as e:
            es = str(e)
            #logging.getLogger().info('ERRX:%s %s:%s @%s'%(es, username, password, self.addr[0]))
            if es.find('PASSWORD_EXPIRED')>=0:
                auth_ok = True
                banner = '<EXPIRED>'
                logging.getLogger().warn( 'FOUND: %s:%s @%s:%d<EXPIRED>' % (username, password, self.addr[0], self.addr[1]) )
            elif es.find('ACCOUNT_DISABLED')>=0 or es.find('ACCOUNT_LOCKED')>=0 or es.find('LOGON_TYPE')>=0 \
                 or es.find('NO_LOGON_SERVERS')>=0 or es.find('NETLOGON_NOT_STARTED')>=0 or es.find('TRUSTED_RELATIONSHIP')>=0\
                or es.find('ACCESS_DENIED')>=0:
                #logging.getLogger().info('ERR:2 %s:%s @%s:%d [%s]'%(username, password, self.addr[0], self.addr[1], self.geterr(es)))
                user_ok = False
            elif es.find('WRONG_PASSWORD')>=0 or es.find('LOGON_FAILURE')>=0:
                pass
            else:
                logging.getLogger().info('ERR:3 %s:%s @%s:%d [%s]'%(username, '*' , self.addr[0], self.addr[1], self.geterr(es)))
                raise#for test
        finally:
            try:
                smbConnection.close()
            except:
                pass
            del smbConnection
        return conn_ok,user_ok,auth_ok,banner


class SmbBruteTester:
    def __init__(self, userdict, passwords = None):
        self.userdict = userdict
        pass
    
    def test(self, task):
        (host,port) = (task[0],task[1])
        rs = []
        auth = SmbAuth( (host,port) )
        for username in self.userdict:
            for password in self.userdict[username]:
                conn_ok,user_ok,auth_ok,banner = auth.login(username, password)
                if not conn_ok:
                    return rs
                if not user_ok:
                    break # next user
                if not auth_ok:
                    continue
                rs.append([host, port, 'SMB', username, password, encode_utf8(banner) if banner else ''])
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
    tester = SmbBruteTester(userdict)
    rs = tester.test( (host,port) )
    print rs
    
