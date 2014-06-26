### Armory Agent
## Memory monitoring

import cherrypy, psutil, os, sys, commands, re
import json
import time
import subprocess
from cherrypy import expose
from genshi.template import TemplateLoader
loader = TemplateLoader('templates', auto_reload=True)

class Timer:
    """
    The timer class
    """

    def __init__(self, duration):
        self.duration = duration
        self.start()

    def start(self):
        self.target = time.time() + self.duration

    def reset(self):
        self.start()

    def set(self, duration):
        self.duration = duration

    def finished(self):
        return time.time() > self.target

# Class to grab FS
class glancesGrabFs:
    """
    Get FS stats
    """

    def __init__(self):
        """
        Init FS stats
        """
        # Ignore the following FS name
        self.ignore_fsname = ('', 'cgroup', 'fusectl', 'gvfs-fuse-daemon',
                              'gvfsd-fuse', 'none')

        # Ignore the following FS type
        self.ignore_fstype = ('autofs', 'binfmt_misc', 'configfs', 'debugfs',
                              'devfs', 'devpts', 'devtmpfs', 'hugetlbfs',
                              'iso9660', 'linprocfs', 'mqueue', 'none',
                              'proc', 'procfs', 'pstore', 'rootfs',
                              'securityfs', 'sysfs', 'usbfs')

        # ignore FS by mount point
        self.ignore_mntpoint = ('', '/dev/shm', '/lib/init/rw', '/sys/fs/cgroup')

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.fs_list = []

        # Open the current mounted FS
        fs_stat = psutil.disk_partitions(all=True)
        for fs in range(len(fs_stat)):
            fs_current = {}
            fs_current['device_name'] = fs_stat[fs].device
            if fs_current['device_name'] in self.ignore_fsname:
                continue
            fs_current['fs_type'] = fs_stat[fs].fstype
            if fs_current['fs_type'] in self.ignore_fstype:
                continue
            fs_current['mnt_point'] = fs_stat[fs].mountpoint
            if fs_current['mnt_point'] in self.ignore_mntpoint:
                continue
            try:
                fs_usage = psutil.disk_usage(fs_current['mnt_point'])
            except Exception:
                continue
            fs_current['size'] = fs_usage.total
            fs_current['used'] = fs_usage.used
            fs_current['avail'] = fs_usage.free
            self.fs_list.append(fs_current)

    def get(self):
        self.__update__()
        return self.fs_list

# Temperature
class glancesGrabSensors:
    """
    Get sensors stats using the PySensors library
    """

    def __init__(self):
        """
        Init sensors stats
        """
        try:
            sensors.init()
        except Exception:
            self.initok = False
        else:
            self.initok = True

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.sensors_list = []

        # grab only temperature stats
        if self.initok:
            for chip in sensors.iter_detected_chips():
                for feature in chip:
                    sensors_current = {}
                    if feature.name.startswith('temp'):
                        sensors_current['label'] = feature.label[:20]
                        sensors_current['value'] = int(feature.get_value())
                        self.sensors_list.append(sensors_current)

    def get(self):
        self.__update__()
        return self.sensors_list

    def quit(self):
        if self.initok:
            sensors.cleanup()

class Converter(object):
    
    @expose
    def bytes2human(self, n):
        '''
        http://code.activestate.com/recipes/578019
        >>> bytes2human(10000)
        '9.8K'
        >>> bytes2human(100001221)
        '95.4M'
        '''
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i+1)*10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)
        return '%sB' % n
    
    @expose
    def memory(self, type):
        mem = psutil.phymem_usage()
        if type == 'used':
            return self.bytes2human(mem.used)
        if type == 'total':
            return self.bytes2human(mem.total)
        if type == 'free':
            return self.bytes2human(mem.free)
        else:
            return 'You forget to pass the type(used,total or free)'

    @expose
    def swap(self, type):
        '''Return swap usage: used, total and free'''
        swap = psutil.swap_memory()
        if type == 'used':
            return self.bytes2human(swap.used)
        if type == 'total':
            return self.bytes2human(swap.total)
        if type == 'free':
            return self.bytes2human(swap.free)
        else:
            print 'You forget to pass the type(used,total or free)'

    @expose
    def cpu(self, type):
        self.cpu1m  = os.getloadavg()[0]
        self.cpu5m  = os.getloadavg()[1]
        self.cpu15m  = os.getloadavg()[2]
        cputimes = psutil.cpu_times_percent
        num_cpus = psutil.NUM_CPUS
        cpu_percent = psutil.cpu_percent()
        if type == 'total_cpu':
            return '%s' %  num_cpus
        if type == 'cpupercent':
            return '%s' % cpu_percent
        if type == 'load1':
            return '%s' % self.cpu1m
        if type == 'load5':
            return '%s' % self.cpu5m
        if type == 'load15':
            return '%s' % self.cpu15m
        if type == 'cputimes':
            return '{0}'.format(cputimes())

    @expose
    def hostname(self):
        return json.dumps(os.uname()[1])

    @expose 
    def disk_partitions(self):
        #partitions = psutil.disk_partitions(all=False)
        #return json.dumps(partitions[0])
        disks = glancesGrabFs()
        return disks.get()

    @expose
    def disk_usage(self,type):
        return str(psutil.disk_usage(type))
        #return glancesGrabSensors.get()

    @expose
    def process(self,type):
        list = psutil.get_pid_list()
        if type == 'total_process':
            return '{0}'.format(len(list))
        if type == 'processname':
            for pid in list:
                p = psutil.Process(pid)
                return p.name

    @expose
    def users(self):
        return psutil.get_users()

    @expose
    def inventory(self):
        command = commands.getoutput('dmidecode -s').split('\n')
        for p in command:
            if re.search('^ ', p):
                a = '%-25s: %s' % (p.strip(), \
                    commands.getoutput('dmidecode -s %s' % p))
                print a
        
    @expose
    def index(self):
        tmpl = loader.load('index.html')
        stream = tmpl.generate(Converter = Converter())
        html = stream.render('xhtml')
        return html

cherrypy.quickstart(Converter())