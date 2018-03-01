#!/usr/bin/env python
# coding=utf-8

import logging

_loggingHandler = None
def initLogger(logfile, level=logging.INFO):
    global _loggingHandler
    logger = logging.getLogger()
    hdlr = logging.FileHandler(logfile)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(level)
    _loggingHandler = hdlr
    return logger

def closeLogger():
    global _loggingHandler
    if _loggingHandler:
        logger = logging.getLogger()
        logger.removeHandler(_loggingHandler)
        del _loggingHandler
        _loggingHandler = None

def encode_utf8(txt):
    if not txt:
        return ''
    otxt = ''
    try:
        otxt = txt.decode('gbk').encode('utf-8')
    except:
        try:
            otxt = txt.decode('utf-8').encode('utf-8')
        except:
            try:
                otxt = txt.encode('utf-8')
            except:
                otxt = '%r' % (txt)
    return otxt
        
