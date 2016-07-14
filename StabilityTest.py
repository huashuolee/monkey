# -*- coding: utf-8 -*-

import time, os, random, threading, subprocess

import sys

import pylog
import json
import shutil
import STQueue

##配置参数
TestMin = 2000  # 测试时间，分钟
TimeOut = 1000  # 超时时间（秒）
eventTimes = 500  # 事件次数
delay = 500  # 两个事件间的延迟


class StabilityTest():
    def __init__(self):
        self.testTime = TestMin
        self.localTime = time.time()
        self.timeout = TimeOut  # second
        self.eventTimes = eventTimes
        self.delay = delay
        self.logDir = u'crashlog'
        if not os.path.exists(self.logDir):
            os.mkdir(self.logDir)

    def setup(self):
        ranStr = time.strftime("%Y-%m-%d_%H%M%S", time.localtime())
        self.seed = random.randint(1000000, 9999999)
        self.logPath = os.path.join(self.logDir, 'log_%s.txt' % ranStr)
        self.screenPath = os.path.join(self.logDir, r'screenshot_%s.png' % ranStr)
        self.crashJsonDir = r'\\192.168.1.112\share\report\OSCrash_json'
        self.crashJson = os.path.join(self.crashJsonDir, (r'crash_%s.json' % ranStr))

        self.screenPathTargetDir = r'\\192.168.1.112\share\report\OSCrash_log\monkey\pic'
        self.screenPathTarget = os.path.join(self.screenPathTargetDir, (r'screenshot_%s.png' % ranStr))
        self.logPathTargetDir = r'\\192.168.1.112\share\report\OSCrash_log\monkey\log'
        self.logPathTarget = os.path.join(self.logPathTargetDir, (r'log_%s.txt' % ranStr))  # 备份crashlog的路径

    #         self.logcatPath = os.path.join(self.logDir, r'logcat_%s.txt' % ranStr)


    def run(self, devices=100):
        global targetDevicesList
        targetDevicesList = []
        devicesList = self.getDevicesList()
        if devices < 100:
            for d in len(devices):
                targetDevicesList.append(devicesList[d])
        else:
            targetDevicesList = devicesList
        tp = STQueue.ThreadPool(len(targetDevicesList))
        i = 1
        while time.time() - self.localTime < self.testTime * 60:
            while not targetDevicesList:
                time.sleep(5)
            self.setup()
            deviceTarget = targetDevicesList.pop()
            cmd_part = '-s %s' % deviceTarget

            runTarget = self.runPackages()  # swith: runPackages()  , runBlaskList(cmd_part)  #debug
            #             logcatClass = self.makeLogcat(cmd_part)  ##add logcat
            time.sleep(1)

            def test_job(mytuple, x=1):
                deviceTarget, runTarget, seed, eventTimes, delay, logPath = mytuple
                # deviceTarget,runTarget=runTarget, seed=seed, eventTimes=eventTimes, delay=delaey, logPath=logPath
                print "adb -s %s shell monkey %s \
                     -s %s -v %s --throttle %s  --monitor-native-crashes --kill-process-after-error --ignore-timeouts \
                    --pct-touch 50 --pct-motion 25 --pct-trackball 15 --pct-syskeys 5 --pct-appswitch 5  > %s" % (
                deviceTarget, runTarget, seed, eventTimes, delay, logPath)
                try:
                    t = threading.Thread(target=os.system, args=("adb -s %s shell monkey %s \
                     -s %s -v %s --throttle %s  --monitor-native-crashes --kill-process-after-error --ignore-timeouts \
                    --pct-touch 50 --pct-motion 25 --pct-trackball 15 --pct-syskeys 5 --pct-appswitch 5  > %s" % (
                    deviceTarget, runTarget, seed, eventTimes, delay, logPath),))
                    t.start()
                    t.join(self.timeout)
                except:
                    pylog.log.error('执行错误')
                    time.sleep(15)
                finally:
                    global targetDevicesList
                    targetDevicesList.append(deviceTarget)

            pylog.log.info("add_job:%s" % deviceTarget)
            tp.add_job(test_job, deviceTarget, runTarget, self.seed, self.eventTimes, self.delay, self.logPath)
            pylog.log.info("wait_complete_in_thread:%s" % deviceTarget)
            self.wait_complete_in_thread(self.teardown, cmd_part, self.logPath, self.crashJson, deviceTarget)

            pylog.log.info("第 %s 次测试" % i)
            i += 1

    def teardown(self, logPath, crashJson, arg=''):
        pylog.log.info('teardown!')
        self.stop(arg)
        #         self.stopLogcat(arg)  ##stop logcat
        self.getPic(arg)
        self.filterCrashLog(logPath, crashJson, arg='')
        if random.randint(1, 10) <= 2:  # 随机清空应用数据
            self.clearAppData(arg)
            pylog.log.info('清空app数据！')
        return

    def wait_complete_in_thread(self, callable, args, logPathT, crashJsonT, jobTarget):
        global targetDevicesList

        def monitorComplet():
            while jobTarget not in targetDevicesList:
                time.sleep(5)
            return callable(logPathT, crashJsonT, args)

        mc = threading.Thread(target=monitorComplet)
        mc.start()

    def makeLogcat(self, arg=''):
        cmd = 'adb -s %s logcat *:E' % arg
        #         os.system('adb logcat *:E >%s' % self.logcatPath)
        logcatC = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return logcatC

    def stopLogcat(self, logcatC, arg=''):
        logcatC.terminate()
        logcatStr = logcatC.stdout.read()
        logcatObj = open(self.logcatPath, 'w')
        logcatObj.write(logcatStr)
        logcatObj.close()
        os.system('adb -s %s logcat -c' % arg)

        proListClass = os.popen("adb -s %s shell ps" % arg)  # get process list
        proListStr = proListClass.read()
        proList = proListStr.split('\r\n')
        pid = 0
        for one in proList:
            if one.find('monkey') > -1:
                fields = one.split(' ')
                for field in fields:
                    if field == '':
                        fields.remove('')
                        fields.remove('')
                pid = fields[1]
                os.system("adb -s %s shell kill -s %s" % (arg, pid))
        return

    def getDevicesList(self):
        devicesClass = os.popen('adb devices')
        devicesInfoList = devicesClass.readlines()
        devicesList = []
        devicesInfoList.remove('\n')
        for i in range(len(devicesInfoList)):
            if i > 0:
                devicesName = devicesInfoList[i].split('\t')[0]
                devicesList.append(devicesName)
        return devicesList

    def runPackages(self):
        return ' '  # -p com.chaozhuo.browser -p com.chaozhuo.filemanager

    def runBlaskList(self, arg=''):
        blacklistFilePath = 'blacklist.txt'  ##self.makeBlacklist()
        os.system('adb -s %s push %s  /data' % (arg, blacklistFilePath))
        return '--pkg-blacklist-file /data/%s' % blacklistFilePath

    def makeBlacklist(self, blacklistFile='blacklist.txt'):
        blacklistClass = os.popen("adb shell pm list packages ")
        blacklistStr = blacklistClass.read()
        blacklistR = blacklistStr.replace('package:', '')
        blacklist = blacklistR.split('\r\n')
        for blackone in blacklist:
            if blackone.find('com.android.systemui') > -1:
                #             if blackone.find('chaozhuo')>-1 or blackone.find('com.android.systemui')>-1:
                blacklist.remove(blackone)
        blacklistRR = '\r\n'.join(blacklist)
        fObj = open(blacklistFile, 'w')
        fObj.write(blacklistRR)
        fObj.close()
        return blacklistFile

    def getPic(self, arg=''):
        os.system("adb -s %s shell /system/bin/screencap -p /sdcard/screenshot.png" % arg)
        os.system("adb -s %s pull /sdcard/screenshot.png %s" % (arg, self.screenPath))

    def stop(self, arg=''):
        devicesID = []
        if not arg:
            devicesID = self.getDevicesList()
        else:
            devicesID.append(arg)
        for deviceID in devicesID:
            print deviceID
            proListClass = os.popen("adb -s %s shell ps" % deviceID)  # get process list
            proListStr = proListClass.read()
            proList = proListStr.split('\r\n')
            print proListStr
            pid = 0
            for one in proList:
                if one.find('monkey') > -1:
                    fields = one.split(' ')
                    for field in fields:
                        if field == '':
                            fields.remove('')
                            fields.remove('')
                    pid = fields[1]
                    os.system("adb -s %s shell kill -s %s" % (deviceID, pid))

    def clearAppData(self, arg=''):
        proListClass = os.popen('adb -s %s shell su -c "ps"' % arg)  # get process list
        proList = proListClass.readlines()
        for one in proList:
            if one.find('com.chaozhuo.filemanager') > -1:  ##删除文管数据
                fields = one.split(' ')
                for field in fields:
                    if field == '':
                        fields.remove('')
                        fields.remove('')
                pid = fields[1]

                os.system('adb -s %s shell su -c "kill -s %s"' % (arg, pid))

                time.sleep(2)
                delcmd = 'adb -s %s shell su -c "rm -f /data/data/com.chaozhuo.filemanager/shared_prefs/PhoenixCommon.xml"' % arg
                os.system(delcmd)

            if one.find('com.chaozhuo.browser') > -1:  ##删除浏览器数据
                fields = one.split(' ')
                for field in fields:
                    if field == '':
                        fields.remove('')
                        fields.remove('')
                pid = fields[1]

                os.system('adb -s %s shell su -c "kill -s %s"' % (arg, pid))
                time.sleep(2)

                delcmd = 'adb -s %s shell su -c "rm -rf /data/data/com.chaozhuo.browser/app_chromeshell/Default"' % arg
                os.system(delcmd)
                delcmd = 'adb -s %s shell su -c "rm -rf /data/data/com.chaozhuo.browser/app_tabs"' % arg
                os.system(delcmd)

    def parseLog(self, logPath):
        pylog.log.info('parseLog:\nlogPath: %s' % logPath)
        fileObj = open(logPath, 'r')
        logList = fileObj.readlines()
        fileObj.close()
        crassInfo = []
        flag = 0
        lineNum = 0
        for one in logList:
            lineNum += 1
            if one.find('// CRASH: ') > -1:
                flag = 1
                crashLineNum = lineNum
            elif one.find('// Short Msg:') > -1:
                className = one.split(':')[1]
            elif one.find('// Long Msg:') > -1:
                message = one.split(':')[2]
            elif one.find('// Build Time:') > -1:
                infoTime = one.split(':')[1]
            #             ##ANR
            #             elif one.find('ANR in ')>-1:
            #                 crassInfo.append(one)
            #                 crassInfo.append(os.path.join(self.logPathTargetDir,os.path.basename(logPath)))
            #                 flag = 2
            #                 break
            ##判断结束
            elif one.find('** Monkey aborted due to error.') > -1:
                flag = 0
                break
            if flag == 1 and lineNum > (crashLineNum + 5):
                crassInfo.append(one[2:])

        if crassInfo:
            if len(crassInfo) > 2:  # crash
                crassInfoDict = {}
                crassInfoDict['time'] = infoTime.strip()
                crassInfoDict['stack'] = ''.join(crassInfo).strip()
                crassInfoDict['net_type'] = 'wifi'
                crassInfoDict['class_name'] = className.strip()
                crassInfoDict['app_version'] = '1.0'
                crassInfoDict['message'] = message.strip()
            #             else:  #ANR
            #                 crassInfoDict = {}
            #                 crassInfoDict['time'] = time.time()*1000
            #                 crassInfoDict['stack'] = crassInfo[1].strip()
            #                 crassInfoDict['net_type'] = 'wifi'
            #                 crassInfoDict['class_name'] = crassInfo[0].strip()
            #                 crassInfoDict['app_version'] = '1.0'
            #                 crassInfoDict['message'] = crassInfo[0].strip()
            crassInfoDict['file_path'] = logPath
            try:
                crassInfoDict['pic_path'] = self.screenPathTarget
            except:
                pass
            return crassInfoDict
        else:

            return False

    def filterCrashLog(self, logPath, crashJsonPath, arg=''):
        crassInfoDict = self.parseLog(logPath)
        if crassInfoDict:
            jsonCrashResult = self.rawJson(crassInfoDict, arg)
            fileObj = open(crashJsonPath, 'w')
            fileObj.write(jsonCrashResult)
            fileObj.close()
            """

            try:
                self.getPic(arg)
                shutil.copy(self.screenPath, self.screenPathTarget)
                shutil.copy(self.logPath, self.logPathTarget)  # debug
            except:
                pylog.log.error('截图没有保存到112')
            """
            pylog.log.error(os.path.basename(crashJsonPath))
            try:
                pylog.log.error(os.path.dirname(self.logPathTarget) + '//' + os.path.basename(crashJsonPath))  # debug
                shutil.copy(crashJsonPath,
                            #os.path.dirname(self.logPathTarget) + '\\' + os.path.basename(crashJsonPath))  # debug
                            os.path.dirname(self.logPathTarget) + '//' + os.path.basename(crashJsonPath))  # debug

            except:
                pylog.log.error('crash文件没有copy：%s' % crashJsonPath)

    def getDeviceInfo(self, arg=''):
        #deviceInfoClass = os.popen("adb -s %s shell cat /system/build.prop" % arg)
        deviceInfoClass = os.popen("adb shell cat /system/build.prop")

        deviceInfoStr = deviceInfoClass.read()
        if deviceInfoStr == '':
            pylog.log.error('可能没有连接设备！')
            return {}
        deviceInfoList = deviceInfoStr.split('\r\n')
        pid = 0
        manufacturer, deviceName, sdkName, productName, brandName, modelName = '', '', '', '', '', ''
        #         print deviceInfoList
        for one in deviceInfoList:
            if one.find('ro.product.manufacturer=') > -1:
                manufacturer = one.split('=')[1]
                continue
            elif one.find('ro.product.device=') > -1:
                deviceName = one.split('=')[1]
                continue
            elif one.find('ro.build.version.sdk=') > -1:
                sdkName = one.split('=')[1]
                continue
            elif one.find('ro.product.name=') > -1:
                productName = one.split('=')[1]
                continue
            elif one.find('ro.product.brand=') > -1:
                brandName = one.split('=')[1]
                continue
            elif one.find('ro.product.model=') > -1:
                modelName = one.split('=')[1]
                continue
        device_info_dict = {}
        device_info_dict["net_type"] = 'wifi'
        device_info_dict["manufacturer"] = manufacturer
        device_info_dict["device"] = deviceName
        device_info_dict["sdk_int"] = sdkName
        device_info_dict["product"] = productName
        device_info_dict["brand"] = brandName
        device_info_dict["model"] = modelName
        return device_info_dict

    def rawJson(self, crassInfoDict, arg=''):  # = self.parseLog('d:\\log.txt')
        resultDict = {}
        resultDict_error_infos = []
        resultDict_error_infos.append(crassInfoDict)  # debug
        resultDict_app_version = {"app_version": "1.0"}
        resultDict_mid = {"mid": "71c0234983f1b7f3e82611de1e59ec6b"}
        try:
            resultDict_pic = {"pic_path": self.screenPathTarget}
        except:
            resultDict_pic = {"pic_path": 'null'}
        try:
            resultDict_pic = {"log_path": self.logPathTarget}
        except:
            resultDict_pic = {"log_path": 'null'}

        resultDict["device_info"] = self.getDeviceInfo(arg)
        resultDict["error_infos"] = resultDict_error_infos
        resultDict.update(resultDict_app_version)
        resultDict.update(resultDict_mid)
        resultDict.update(resultDict_pic)
        resultDictJson = json.dumps(resultDict)
        return resultDictJson


def parseLogs(logDir):
    ST = StabilityTest()

    for dirpath, dirnames, filenames in os.walk(logDir):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            print "====="+filePath
            #ST.filterCrashLog(filePath, r'\\192.168.1.112\share\report\OSCrash_json\%s.json' % file)

            # filePath = /home/huashuolee/data/work/dailywork/20160616/20160608/log_2016-05-25_213454.txt
            ST.filterCrashLog(filePath, r'/home/huashuolee/data/work/tmp/OSCrash_json/%s.json' % file)


if __name__ == "__main__":

    #parseLogs(r'\\file\share\report\OSCrash_log\monkey')

    #parseLogs(r'/home/huashuolee/work/dailywork/20160616/20160608')

    #parseLogs(sys.argv[1])

    StabilityTest().run()

    #     StabilityTest().run()
    #     StabilityTest().stop()
    #     print StabilityTest().getDevicesList()
    #         StabilityTest().multiRun()
    #     StabilityTest().makeBlacklist()
    #     StabilityTest().clearAppData()
    #     print StabilityTest().rawJson()
