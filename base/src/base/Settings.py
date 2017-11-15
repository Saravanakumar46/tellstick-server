# -*- coding: utf-8 -*-

import os
import json
import logging
import shutil
import time
from threading import Timer
from .Application import Application
from configobj import ConfigObj, ParseError
from board import Board

class Settings(object):
	_config = None
	_lastWrite = None
	_writeTimer = None

	def __init__(self, section):
		super(Settings, self).__init__()
		self.section = section

		if Settings._config is None:
			self.configPath = Board.configDir()
			if not os.path.exists('%s/telldus' % self.configPath):
				os.makedirs('%s/telldus' % self.configPath)
			self.configFilename = 'Telldus.conf'
			self.__loadFile()
			Application().registerShutdown(self.__shutdown)
		if section not in Settings._config:
			Settings._config[section] = {}

	def get(self, name, default):
		value = self[name]
		if value is None:
			return default
		if isinstance(default, dict) or isinstance(default, list):
			value = json.loads(value)
		if isinstance(default, int):
			value = int(value)
		return value

	def __loadFile(self):
		path = self.configPath + '/' + self.configFilename
		backuppath = self.configPath + '/telldus/' + self.configFilename
		try:
			Settings._config = ConfigObj(path)
			return
		except ParseError as error:
			logging.critical('Could not load settings file: %s', error)
		# Loading failed. Try backup.
		# Copy faulty config for later analysis
		shutil.copy(path, '%s.err' % backuppath)
		try:
			# Read backup
			Settings._config = ConfigObj('%s.bak' % backuppath)
			Settings._config.filename = path
			# Success, copy a backup of this file for later analysis
			shutil.copy('%s.bak' % backuppath, '%s.bak.err' % backuppath)
			return
		except ParseError as error:
			logging.critical('Could not load backup settings file: %s', error)
		# Start with empty one
		Settings._config = ConfigObj()
		Settings._config.filename = path

	def __shutdown(self):
		if Settings._writeTimer is not None:
			Settings._writeTimer.cancel()
			self.__writeTimeout()

	@staticmethod
	def __writeTimeout():
		Settings._writeTimer = None
		Settings._lastWrite = time.time()
		Settings._config.filename
		backuppath = os.path.dirname(Settings._config.filename) + '/telldus/' + os.path.basename(Settings._config.filename)
		with open('%s.1' % backuppath, 'wb') as fd:
			Settings._config.write(fd)
			fd.flush()
		# Create backup
		shutil.copy('%s.1' % backuppath, '%s.bak' % backuppath)
		# Do not us shutils for rename. We must ensure an atomic operation here
		os.rename('%s.1' % backuppath, Settings._config.filename)

	def __writeToDisk(self):
		if Settings._writeTimer is not None:
			return
		if Settings._lastWrite is None or (time.time() - Settings._lastWrite) > 300:
			Settings._writeTimer = Timer(1.0, self.__writeTimeout)
		else:
			Settings._writeTimer = Timer(300.0, self.__writeTimeout)
		Settings._writeTimer.start()

	def __getitem__(self, name):
		try:
			value = Settings._config[self.section][name]
		except KeyError:
			return None
		return value

	def __setitem__(self, name, value):
		if isinstance(value, dict) or isinstance(value, list):
			value = json.dumps(value)
		Settings._config[self.section][name] = value
		self.__writeToDisk()
