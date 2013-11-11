### Armory Agent
## Memory monitoring

import cherrypy, psutil, os
from cherrypy import expose
from genshi.template import TemplateLoader
loader = TemplateLoader('templates', auto_reload=True)

class Converter:
	
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

	@expose
	def hostname(self):
		return os.uname()[1]

	@expose 
	def disks(self):
		partitions = psutil.disk_partitions(all=False)
		return partitions[0]

	@expose
	def index(self):
		tmpl = loader.load('index.html')
		stream = tmpl.generate(Converter = Converter())
		html = stream.render('xhtml')
		return html	

cherrypy.quickstart(Converter())