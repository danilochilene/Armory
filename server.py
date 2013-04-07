### Armory server

import requests, threading, pymongo

mongo = pymongo.Connection('localhost')
mongo_db = mongo['armory']
mongo_collection = mongo_db['memory']

def do_every (interval, worker_func, iterations = 0):
	if iterations != 1:
		threading.Timer (
			interval,
			do_every, [interval, worker_func, 0 if iterations == 0 else iterations-1]
		).start ();

	worker_func ();

def get_memory():
	r = requests.get('http://localhost:8080/memory?type=used')
	print r.content
	insert_id = mongo_collection.insert({
		'used': r.content
		})

do_every(10, get_memory)