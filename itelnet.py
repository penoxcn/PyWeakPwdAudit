r"""TELNET client class.
Based on RFC 854: TELNET Protocol Specification, by J. Postel and
J. Reynolds
"""

# Imported modules
import re
import errno
import sys
import socket
import time
import select

__all__ = ["Telnet"]

# Tunable parameters
DEBUGLEVEL = 0
# Telnet protocol defaults
TELNET_PORT = 23
TELNET_CONN_TIMEOUT = 6.0
TELNET_READ_TIMEOUT = 6.0

# Telnet protocol characters (don't change)
IAC  = chr(255) # "Interpret As Command"
DONT = chr(254)
DO   = chr(253)
WONT = chr(252)
WILL = chr(251)
SE  = chr(240)  # Subnegotiation End
SB =  chr(250)  # Subnegotiation Begin
theNULL = chr(0)
ECHO = chr(1) # echo
SGA = chr(3)
STATUS = chr(5) # give status
TTYPE = chr(24) # terminal type
NAWS = chr(31) # window size
TSPEED = chr(32) # terminal speed
LFLOW = chr(33) # remote flow control
LINEMODE = chr(34) # Linemode option
XDISPLOC = chr(35) # X Display Location
AUTHENTICATION = chr(37) # Authenticate
NEWENV = chr(39) # New - Environment variables

class Telnet:

    re_login = re.compile(r'\b(username|login|user|User Name)\s*:', re.I)
    re_password = re.compile(r'\b(password|passcode|passwd)\s*:', re.I)
    re_shell = re.compile(r'([^\r\n]*[>%\$#]|\b[A-Z]:\\\\)\s*$')
    #"\x1b[35m# \x1b[0m"
    re_ok = re.compile('Telnet client was connected')
    re_failed = re.compile('|'.join(
        ('Authentication fail',
        'Login invalid',
        'Login incorrect',
        'Bad Username'
        'Bad password',
        'is incorrect',
        'is rejected',
        'invalid login',
        'Access denied',
        '% Login failed',
        'is invalid',
        'Please retry',
        'password fail',
        'not exist',
        'Authentication fail',
        'try later',
        'Login failed',
        'Invalid domain',
        )
        ), re.I)
    re_ignore = re.compile('|'.join(
        ('Polycom Command Shell',
         'Polycom RMX',
         r'/>\s*Version:',
         'Model name',
         'Vcom3232',
         'UPS SNMP Agent',
         'HP JetDirect',
         'telnet_debug',
         'your choice:',
         'Enter Choice>',
         r'Type "help or \?" for information',
         'RICOH Maintenance',
         'SHARP CORPORATION',
         r'HTTP/\d\.\d',
         'psh running',
         'APPFS Ver',
         'WebPower Configuration',
         'Selection:',
         'PrintServer',
         'KYOCERA',
         'NetDVRDVS:',
         'Type <return>',
         'input hostname',
         'DMPS3-300-C Console',
         'CP3 Console',
         )
         ), re.I)
    
    def __init__(self, host=None, port=TELNET_PORT,
                 timeout=TELNET_CONN_TIMEOUT):
        """Constructor.
        """
        self.debuglevel = DEBUGLEVEL
        self.host = host
        self.port = port
        self.timeout = timeout
        self.waiting = 0
        self.sock = None
        self.rawq = ''
        self.irawq = 0
        self.cookedq = ''
        self.eof = False
        self.iacseq = '' # Buffer for IAC sequence.
        self.sb = 0 # flag for SB and SE sequence.
        self.env = None
        self.sbdataq = ''
        
        if host is not None:
            self.open(host, port, timeout)

    def open(self, host, port=TELNET_PORT, timeout=TELNET_CONN_TIMEOUT):
        self.eof = False
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = socket.create_connection((host, port), timeout)
        
    def __del__(self):
        self.close()

    def msg(self, msg, *args):
        if self.debuglevel > 0:
            print 'Telnet(%s,%s):' % (self.host, self.port),
            if args:
                print msg % args
            else:
                print msg

    def set_debuglevel(self, debuglevel):
        self.debuglevel = debuglevel

    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = 0
        self.eof = True
        self.iacseq = ''
        self.sb = 0

    def read_some(self, timeout=3.0, min_bytes=9):
        self.sock.settimeout(0.8)
        self.negotiate()
        start = time.time()
        lastgood = start
        elapsed = 0
        #print '%.2f %d bytes' % (elapsed, len(self.cookedq))
        while not self.eof and elapsed<timeout:
            now = time.time()
            elapsed = now - start
            try:
                self.process_rawq()
                #print '%.2f %d bytes' % (elapsed, len(self.cookedq))
                self.fill_rawq()
                lastgood = now
            except socket.timeout:
                #print '%.2f timeout' % (elapsed)
                if len(self.cookedq)==0 or (len(self.cookedq)<min_bytes and (now-lastgood)<3.1) or now-lastgood<2.3:
                    continue
                break #
            except Exception as e:
                #print '%.2f error' % (elapsed)
                self.eof = True
                break
        buf = self.cookedq
        #print '%.2f %d bytes' % (elapsed, len(self.cookedq))
        self.cookedq = ''
        self.sock.settimeout(TELNET_READ_TIMEOUT)
        return buf

    def parse_banner(self, buf):
        founds = Telnet.re_ignore.findall(buf)
        if founds:
            return 'IGNORE', '||'.join(founds)
        founds = Telnet.re_login.findall(buf)
        if founds:
            return 'LOGIN', '||'.join(founds)
        founds = Telnet.re_password.findall(buf)
        if founds:
            return 'PASSWORD', '||'.join(founds)
        founds = Telnet.re_shell.findall(buf)
        if founds:
            return 'SHELL', '||'.join(founds)
        return 'OTHER', buf

    def parse_auth(self, buf):
        founds = Telnet.re_password.findall(buf)
        if founds:
            return 'PASSWORD', '||'.join(founds)
        founds = Telnet.re_login.findall(buf)
        if founds:
            return 'LOGIN', '||'.join(founds)
        founds = Telnet.re_failed.findall(buf)
        if founds:
            return 'FAILED', '||'.join(founds)
        founds = Telnet.re_ignore.findall(buf)
        if founds:
            return 'IGNORE', '||'.join(founds)
        founds = Telnet.re_shell.findall(buf)
        if founds:
            return 'SHELL', '||'.join(founds)
        founds = Telnet.re_ok.findall(buf)
        if founds:
            return 'LOGOK', '||'.join(founds)
        if buf.find('# \x1b[0m')>0:
            return 'SHELL','<BUSYBOX>#'
        return 'OTHER', buf
    
    def iseof(self):
        return self.eof

    def write(self, buffer):
        """Write a string to the socket, doubling any IAC characters.
        Can block if the connection is blocked.  May raise
        socket.error if the connection is closed.
        """
        if IAC in buffer:
            buffer = buffer.replace(IAC, IAC+IAC)
        self.msg("send %r", buffer)
        self.sock.sendall(buffer)
        
    def negotiate(self):
        data = IAC+DO+SGA+IAC+WILL+TTYPE+IAC+WILL+NAWS+IAC+WONT+TSPEED+IAC+WONT+LFLOW+IAC+WONT+LINEMODE+IAC+WILL+NEWENV+IAC+DO+STATUS
        try:
            self.sock.sendall(data)
            self.fill_rawq()
            return 1
        except socket.timeout:
            #self.msg('[Telnet] negotiate timeout')
            return 0
        except Exception as e:
            self.eof = True
            #self.msg('[Telnet] negotiate: %s', str(e))
            return -1

    def option_callback(self, cmd, opt):
        data = ''
        if cmd in (DO,WILL):
            if opt==TTYPE:
                data += IAC+SB+TTYPE+theNULL+'LINUX'+IAC+SE
                if self.env:
                    data = IAC+SB+NEWENV+chr(3)+self.env+IAC+SE
                #self.msg('[Telnet] send: %r', data )
            elif opt==NAWS:
                data = IAC+SB+NAWS+theNULL+chr(80)+theNULL+chr(24)+IAC+SE
                #self.msg('[Telnet] send: %s', "IAC+SB+NAWS+theNULL+chr(80)+theNULL+chr(24)+IAC+SE" )
            elif opt==NEWENV:
                if not self.env:
                    data = IAC+SB+NEWENV+theNULL+IAC+SE
                    #self.msg('[Telnet] send: %r', data )
            elif opt==TSPEED:
                data = IAC+SB+TSPEED+'38400,38400'+IAC+SE
                #self.msg('[Telnet] send: %r', data )
            elif opt==ECHO and cmd==WILL:
                data = IAC + DO + ECHO
                #self.msg('[Telnet] send: IAC + DO + ECHO' )
            elif opt==SGA:
                #self.msg('[Telnet] recv: IAC %d SGA' , ord(cmd) )
                pass
            elif cmd==DO:
                data = IAC + WONT + opt
                #self.msg('[Telnet] send: IAC + DONT + %d', ord(opt) )
            else:
                data = IAC + WONT + opt
                #self.msg('[Telnet] send: IAC + WONT + %d', ord(opt) )
        else:
            #self.msg('[Telnet] recv: IAC %d %d', ord(cmd), ord(opt) )
            pass
        if data:
            self.sock.sendall(data)
    

    def process_rawq(self):
        buf = ['', '']
        try:
            while self.rawq:
                c = self.rawq_getchar()
                if c==None:
                    break
                if not self.iacseq:
                    if c == theNULL:
                        continue
                    if c == "\021":
                        continue
                    if c != IAC:
                        buf[self.sb] = buf[self.sb] + c
                        continue
                    else:
                        self.iacseq += c
                elif len(self.iacseq) == 1:
                    # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
                    if c in (DO, DONT, WILL, WONT):
                        self.iacseq += c
                        continue

                    self.iacseq = ''
                    if c == IAC:
                        buf[self.sb] = buf[self.sb] + c
                    else:
                        if c == SB: # SB ... SE start.
                            self.sb = 1
                            self.sbdataq = ''
                        elif c == SE:
                            self.sb = 0
                            self.sbdataq = self.sbdataq +buf[1]
                            if self.sbdataq[0]==TTYPE:
                                self.option_callback(DO, self.sbdataq[0])
                            elif self.sbdataq[0]==NEWENV:
                                self.env = self.sbdataq[2:-2]
                            elif self.sbdataq[0]==TSPEED:
                                self.option_callback(DO, self.sbdataq[0])
                            buf[1] = ''
                        # We can't offer automatic processing of
                        # suboptions. Alas, we should not get any
                        # unless we did a WILL/DO before.
                        else:
                            #self.msg('IAC %d not recognized' % ord(c))
                            pass
                elif len(self.iacseq) == 2:
                    cmd = self.iacseq[1]
                    self.iacseq = ''
                    opt = c
                    if cmd in (DO, DONT):
                        #self.msg('IAC %s %d',cmd == DO and 'DO' or 'DONT', ord(opt))
                        self.option_callback(cmd, opt)
                        #self.sock.sendall(IAC + WONT + opt)
                    elif cmd in (WILL, WONT):
                        #self.msg('IAC %s %d',cmd == WILL and 'WILL' or 'WONT', ord(opt))
                        self.option_callback(cmd, opt)
                        #self.sock.sendall(IAC + DONT + opt)
        except EOFError: # raised by self.rawq_getchar()
            self.iacseq = '' # Reset on EOF
            self.sb = 0
            pass
        except Exception as e: #sendall error
            #self.msg('[Telnet] error2: %s', str(e))
            self.eof = True
            pass
        self.cookedq = self.cookedq + buf[0]
        self.sbdataq = self.sbdataq + buf[1]

    def rawq_getchar(self):
        if not self.rawq:
            try:
                self.fill_rawq()
            except socket.timeout: #timeout
                return None
            except Exception as e: #other unknow error
                self.eof = True
                #self.msg('[Telnet] error3: %s', str(e))
            if self.eof:
                raise EOFError
        c = self.rawq[self.irawq]
        self.irawq = self.irawq + 1
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        return c

    def fill_rawq(self):
        if self.irawq >= len(self.rawq):
            self.rawq = ''
            self.irawq = 0
        # The buffer size should be fairly small so as to avoid quadratic
        # behavior in process_rawq() above
        self.waiting = 1
        buf = self.sock.recv(50)
        self.waiting = 0
        #self.msg("recv %r", buf)
        self.eof = (not buf)
        self.rawq = self.rawq + buf

        
    def sock_avail(self):
        """Test whether data is available on the socket."""
        return select.select([self], [], [], 0) == ([self], [], [])

    
if __name__ == '__main__':
    tn = Telnet(sys.argv[1],int(sys.argv[2]))
    banner = tn.read_some()
    ftype,text = tn.parse_banner(banner)
    print '%r' % (banner)
    print '%s,%r' % (ftype, text)
    if sys.argv[3]:
        tn.write(sys.argv[3]+'\r\n')
        banner = tn.read_some()
        ftype,text = tn.parse_auth(banner)
        print '%r' % (banner)
        print '%s,%r' % (ftype, text)
    if sys.argv[4]:
        tn.write(sys.argv[3]+'\r\n')
        banner = tn.read_some(15)
        ftype,text = tn.parse_auth(banner)
        print '%r' % (banner)
        print '%s,%r' % (ftype, text)        
    tn.close()
