#!/usr/bin/env python
# coding=utf-8

import os
import sys
import time
import xutils
from optparse import OptionParser
from BruteRunner import Bruter
from MssqlBrute import MssqlBruteTester

def main():
    options = OptionParser(usage='%prog [options]', description='BruteScanRun.py')
    options.add_option('-l', '--logfile', type='string', default='BruteScanRun.log', help='log file path')
    options.add_option('-c', '--config', type='string', default='', help='config file path')
    
    opts, args = options.parse_args()
    try:
        logger = xutils.initLogger(opts.logfile)
        if not os.path.isfile(opts.config):
            logger.error('config file {%s} is missing. bye!' % (opts.config) )
            return 1
        #TODO:
        #Please implement your loadConfig
        wcfg = loadConfig(opts.config)
        config = {'threads':wcfg['THREADS'], 'userdict':wcfg['DICTFILE'],
                  'proto':wcfg['PROTO'].lower(),
                  'ports':ports, 'maxruntime':int(wcfg['MAXTIME']),
                  'processes':wcfg['PROCESSES'], 'logfile':opts.logfile, }
        bruter = Bruter(MssqlBruteTester)
        bruter.start(config)
    except Exception as e:
        sys.stderr.write('EXCEPTION: %s, pid: %d, exit.\n'%(str(e), os.getpid()))

if __name__ == '__main__':
    main()

