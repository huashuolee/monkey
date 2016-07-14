#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys

class _StreamHandler(logging.StreamHandler):
    
    def __init__(self):
        logging.StreamHandler.__init__(self, sys.stdout)
        pass
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            fs = "%s\n"
            msg = fs % msg
            if type(msg) != type(u''):
                import chardet #by roc
                if chardet.detect(msg)['encoding']=='GB2312':
                    msg = msg.decode('gbk')
                else:
                    msg = msg.decode('utf-8')
            stream.write(msg.encode(stream.encoding))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

def _init_log_config():
    f = '%(asctime)s %(thread)s %(levelname)s/%(name)s: %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                    format = f,
                    datefmt='%m-%d %H:%M:%S',
                    filename='./pyut.log')
    console = _StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(thread)d %(levelname)s/%(name)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
_init_log_config()
log = logging.getLogger('pyut')


def run():
    log.debug("hello debug")
    log.error('test')

if __name__ == '__main__':
#     run()
    
    pass
