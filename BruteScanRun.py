#!/usr/bin/env python
# coding=utf-8

import os
import sys
import time
from xapps import xapp
from bruter import Bruter
from optparse import OptionParser

def default_ffilter(data,ds):
    return data

def RunMain(confname='', BruteTesterClass=None, ffilter=default_ffilter):
    options = OptionParser(usage='%prog [options]', description='BruteScanRun.py')
    options.add_option('-l', '--logfile', type='string', default='BruteScanRun.log', help='log file path')
    options.add_option('-c', '--config', type='string', default='', help='config file path')

    opts, args = options.parse_args()
    try:
        logger = xapp.initLogger(opts.logfile)
        if not os.path.isfile(opts.config):
            logger.error('config file {%s} is missing. bye!' % (opts.config) )
            return 1
        cfg = xapp.loadConfig(opts.config)
        dbcfg = cfg['DATABASE']
        wcfg = cfg[confname]
        ports = []
        for p in wcfg['PORTS'].split(','):
            p = p.strip()
            if p:
                ports.append(int(p))
        scancfg = {'threads':wcfg['THREADS'], 'userdict':wcfg['DICTFILE'], 'proto':wcfg['PROTO'].lower(),
                   'ports':ports, 'ffilter': ffilter, 'maxruntime':int(wcfg['MAXTIME']),
                   'processes':wcfg['PROCESSES'], 'logfile':opts.logfile}
        bruter = Bruter(BruteTesterClass)
        bruter.start(dbcfg, scancfg)
    except Exception as e:
        import traceback
        sys.stderr.write('EXCEPTION: %s, pid: %d, exit.\n'%(str(e), os.getpid()))
        traceback.print_exc()
    finally:
        os._exit(0)

        
def RunTest(logfile='brute.test.log', dict_file='brute.dict.txt', TesterClass=None):
    logger = xapp.initLogger(logfile)
    host, port = sys.argv[1], int(sys.argv[2])
    pass
