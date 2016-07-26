# -*- coding: utf-8 -*-

import time, os, random, threading, subprocess
import argparse
import sys
import platform

from common import pylog
import json
from common import prints
import shutil

##配置参数
TestMin = 10  # 测试时间，分钟
TimeOut = 10000  # 超时时间（秒）
eventTimes = 5000  # 事件次数
delay = 100  # 两个事件间的延迟
logDir = "crashlog"
jsonDir = logDir + os.sep + "json"
picDir = logDir + os.sep + "pic"


class StabilityTest():
    def __init__(self, device):
        self.testTime = TestMin
        self.localTime = time.time()
        self.timeout = TimeOut  # second
        self.eventTimes = eventTimes
        self.delay = delay
        self.logDir = logDir + os.sep + "raw" + os.sep + device
        prints.print_msg("A", "Test start running: \n\r" + self.logDir)
        self.jsonDir = jsonDir

        if os.path.exists(self.logDir):
            shutil.rmtree(self.logDir)
        if not os.path.exists(self.logDir):
            os.makedirs(self.logDir)
        if not os.path.exists(jsonDir):
            os.makedirs(jsonDir)
        if not os.path.exists(picDir):
            os.makedirs(picDir)
        self.recordDeviceInfo(self.logDir)

    def setup(self):
        ranStr = time.strftime("%Y-%m-%d_%H%M%S", time.localtime())
        self.seed = random.randint(1000000, 9999999)
        self.logPath = os.path.join(self.logDir, 'log_%s.txt' % ranStr)
        self.screenPath = os.path.join(self.logDir, r'screenshot_%s.png' % ranStr)
        """
        self.crashJsonDir = r'\\192.168.1.112\share\report\OSCrash_json'
        self.crashJson = os.path.join(self.crashJsonDir, (r'crash_%s.json' % ranStr))

        self.screenPathTargetDir = r'\\192.168.1.112\share\report\OSCrash_log\monkey\pic'
        self.screenPathTarget = os.path.join(self.screenPathTargetDir, (r'screenshot_%s.png' % ranStr))
        self.logPathTargetDir = r'\\192.168.1.112\share\report\OSCrash_log\monkey\log'
        self.logPathTarget = os.path.join(self.logPathTargetDir, (r'log_%s.txt' % ranStr))  # 备份crashlog的路径
        pylog.log.error(self.logPathTarget)
        """

    def run(self, device):
        deviceTarget = device
        i = 1
        while time.time() - self.localTime < self.testTime * 60:
            pylog.log.error(time.time() - self.localTime)
            self.setup()
            cmd_part = '-s %s' % deviceTarget
            runTarget = self.runPackages()  # swith: runPackages()  , runBlaskList(cmd_part)  #debug
            time.sleep(1)
            pylog.log.info(u"add_job:%s" % deviceTarget)
            pylog.log.info(u"第 %s 次测试" % i)
            self.test_job(deviceTarget, runTarget, self.seed, self.eventTimes, self.delay, self.logPath)
            self.getPic(deviceTarget)
            time.sleep(5)
            i += 1

    def test_job(self, *args):
        deviceTarget, runTarget, seed, eventTimes, delay, logPath = args
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
            pylog.log.error(u'执行错误')
            time.sleep(15)

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

    def recordDeviceInfo(self, arg=''):
        deviceInfoClass = os.popen("adb shell cat /system/build.prop")
        with open(arg + "/deviceInfo.txt", "w") as f:
            for item in deviceInfoClass.read():
                f.write(item)


class parseLogs():
    def __init__(self):
        self.picDir = picDir

    def parseLogs(self, logDir):
        for dirpath, dirnames, filenames in os.walk(logDir):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                if file[:3] == "log":
                    prints.print_msg("E", file)
                    self.filterCrashLog(filePath, jsonDir + r'/%s.json' % file, dirpath, file)
                    # crashlog/raw/xxxxx/logxxxx.txt, crashlog/json/xxxxx.json
                    # dirpath/deviceinfo.txt

    def filterCrashLog(self, logPath, crashJsonPath, dirpath, file):
        crassInfoDict = self.parseLog(logPath)
        if crassInfoDict:
            # cmd = cp screen self.picDir
            self.copypic(dirpath, file)
            deviceinfo = dirpath + "/deviceInfo.txt"
            jsonCrashResult = self.rawJson(crassInfoDict, deviceinfo)
            with open(crashJsonPath, 'w') as fileObj:
                fileObj.write(jsonCrashResult)

    def parseLog(self, logPath):
        pylog.log.info('parseLog:\nlogPath: %s' % logPath)
        with open(logPath, 'r') as fileObj:
            log_list = fileObj.readlines()
        crassInfo = []
        flag = 0
        lineNum = 0
        for one in log_list:
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
            # ##ANR
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
            # else:  #ANR
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

    def getDeviceInfo(self, arg=''):
        with open(arg, "r") as f:
            deviceInfoList = f.readlines()
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

    def rawJson(self, crassInfoDict, arg):  # = self.parseLog('d:\\log.txt')
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

    def copypic(self, dirpath, file):
        filename = "screenshot_" + file[4:22] + "png"
        src = os.path.join(dirpath, filename)
        dst = self.picDir
        try:
            shutil.copy(src, dst)
        except:
            pass


class upload_logs():
    def __init__(self):
        self.l_json = 'crashlog/json'
        self.r_json = "192.168.1.112" + os.sep + "share" + os.sep + "report" + os.sep + "OSCrash_json"

    def copyfile(self):
        ostype = platform.system()
        if ostype == "Linux":
            pass
        elif ostype == "Windows":
            pass


def parseArgs(argv):
    parser = argparse.ArgumentParser()
    # parser.add_argument('start', help="specify the device ID")
    parser.add_argument('-f', dest='formatlog', help="python StabilityTest.py -f crashlog/raw")
    parser.add_argument("-r", help="python StabilityTest.py -r -s 0584e3fc", action="store_true")
    parser.add_argument('-s', dest='sn', help="python StabilityTest.py -r -s 0584e3fc")
    parser.add_argument('-u', dest='uploadLog', help="upload log to server",action="store_true")
    parser.add_argument('--reboot', dest='reboot', help="reboot the device once error occurs")
    args = parser.parse_args()
    if args.formatlog:
        print args.formatlog
        parseLogs().parseLogs(args.formatlog)
    if args.uploadLog:
        prints.print_msg("A",u"请手动拷贝 crashlog/json 到//192.168.1.112/share/report/OSCrash_json")
    if args.r:
        if args.sn:
            deviceid = args.sn
            StabilityTest(deviceid).run(deviceid)
        else:
            prints.print_msg("E", "comman line: \r\n  python StabilityTest.py -r -s 0584e3fc")


if __name__ == "__main__":
    parseArgs(sys.argv[1:])
