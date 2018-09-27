#coding:gbk
import Queue
import threading
import sys
import time
import urllib


class MyThread(threading.Thread):
    def __init__(self, workQueue, resultQueue,timeout=30, **kwargs):
        threading.Thread.__init__(self, kwargs=kwargs)
        #线程在结束前等待任务队列多长时间
        self.timeout = timeout
        self.setDaemon(True)
        self.workQueue = workQueue
        self.resultQueue = resultQueue
        self.start()
    
    def run(self):
        while True:
            try:
                callable, args, kwargs = self.workQueue.get(timeout=self.timeout)
                res = callable(args, kwargs)
                #报任务返回的结果放在结果队列中
#                 self.resultQueue.put(res+" | "+self.getName())    
            except Queue.Empty: #任务队列空的时候结束此线程
                break
            except :
                print sys.exc_info()
                raise
    
class ThreadPool:
    def __init__( self, num_of_threads=10):
        self.workQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self.threads = []
        self.__createThreadPool( num_of_threads )
    
    def __createThreadPool( self, num_of_threads ):
        for i in range( num_of_threads ):
               thread = MyThread( self.workQueue, self.resultQueue )
               self.threads.append(thread)
    
    def wait_for_complete(self, test_target):

        if test_target.isAlive():#判断线程是否还存活来决定是否调用join
            thread.join()
        
             
    def add_job( self, callable, *args, **kwargs ):
        return self.workQueue.put( (callable,args,kwargs) )


def test_job(id,x=1):
    print 'test_job_%s' % id[0]
    time.sleep(10)
    print 'test_job2_end_%s' % id[0]
    testList.append(id[0])
    return str(id)
def done(id):
    print 'done_%s' % id

def test():
    print 'start testing'
    tp = ThreadPool(2)
    global testList
    testList = [111,222]
    while True:   #以后加限制条件
        time.sleep(1)
        while not testList:
            time.sleep(5)
        jobTarget = testList.pop()
        tp.add_job( test_job, jobTarget)
        print 'wait_complete_in_thread'
        tp.wait_complete_in_thread(done,999,jobTarget)
#     #处理结果
#     print 'result Queue\'s length == %d '% tp.resultQueue.qsize()
#     while tp.resultQueue.qsize():
#         print tp.resultQueue.get()
    print 'end testing'
if __name__ == '__main__':
    test()