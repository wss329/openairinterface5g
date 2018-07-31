#/*
# * Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
# * contributor license agreements.  See the NOTICE file distributed with
# * this work for additional information regarding copyright ownership.
# * The OpenAirInterface Software Alliance licenses this file to You under
# * the OAI Public License, Version 1.1  (the "License"); you may not use this file
# * except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.openairinterface.org/?page_id=698
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
# *-------------------------------------------------------------------------------
# * For more information about the OpenAirInterface (OAI) Software Alliance:
# *      contact@openairinterface.org
# */
#---------------------------------------------------------------------
# Python for CI of OAI-eNB + COTS-UE
#
#   Required Python Version
#     Python 3.x
#
#   Required Python Package
#     pexpect
#---------------------------------------------------------------------

#-----------------------------------------------------------
# Version
#-----------------------------------------------------------
Version = '0.1'

#-----------------------------------------------------------
# Import
#-----------------------------------------------------------
import sys		# arg
import re		# reg
import pexpect		# pexpect
import time		# sleep
import os
import xml.etree.ElementTree as ET
import logging
import datetime
import signal
from multiprocessing import Process,Lock
logging.basicConfig(
	level=logging.DEBUG,
	format="[%(asctime)s] %(name)s:%(levelname)s: %(message)s"
)

#-----------------------------------------------------------
# Class Declaration
#-----------------------------------------------------------
class SSHConnection():
	def __init__(self):
		self.eNBIPAddress = ''
		self.eNBRepository = ''
		self.eNBBranch = ''
		self.eNBCommitID = ''
		self.eNBUserName = ''
		self.eNBPassword = ''
		self.eNBSourceCodePath = ''
		self.EPCIPAddress = ''
		self.EPCUserName = ''
		self.EPCPassword = ''
		self.EPCSourceCodePath = ''
		self.EPCType = ''
		self.ADBIPAddress = ''
		self.ADBUserName = ''
		self.ADBPassword = ''
		self.testCase_id = ''
		self.testXMLfile = ''
		self.desc = ''
		self.Build_eNB_args = ''
		self.Initialize_eNB_args = ''
		self.ping_args = ''
		self.ping_packetloss_threshold = ''
		self.iperf_args = ''
		self.iperf_packetloss_threshold = ''
		self.UEDevices = []
		self.UEIPAddresses = []

	def open(self, ipaddress, username, password):
		self.ssh = pexpect.spawn('ssh', [username + '@' + ipaddress], timeout = 5)
		self.sshresponse = self.ssh.expect(['Are you sure you want to continue connecting (yes/no)?', 'password:', 'Last login', pexpect.EOF, pexpect.TIMEOUT])
		if self.sshresponse == 0:
			self.ssh.sendline('yes')
			self.ssh.expect('password:')
			self.ssh.sendline(password)
			self.sshresponse = self.ssh.expect(['\$', 'Permission denied', 'password:', pexpect.EOF, pexpect.TIMEOUT])
			if self.sshresponse == 0:
				pass
			else:
				logging.debug('self.sshresponse = ' + str(self.sshresponse))
				sys.exit('SSH Connection Failed')
		elif self.sshresponse == 1:
			self.ssh.sendline(password)
			self.sshresponse = self.ssh.expect(['\$', 'Permission denied', 'password:', pexpect.EOF, pexpect.TIMEOUT])
			if self.sshresponse == 0:
				pass
			else:
				logging.debug('self.sshresponse = ' + str(self.sshresponse))
				sys.exit('SSH Connection Failed')
		elif self.sshresponse == 2:
			# Checking if we are really on the remote client defined by its IP address
			self.command('stdbuf -o0 ifconfig | egrep --color=never "inet addr:"', '\$', 5)
			result = re.search(str(ipaddress), str(self.ssh.before))
			if result is None:
				sys.exit('SSH Connection Failed: TIMEOUT !!!')
			pass
		else:
			# debug output
			logging.debug(str(self.ssh.before))
			logging.debug('self.sshresponse = ' + str(self.sshresponse))
			sys.exit('SSH Connection Failed!!!')

	def command(self, commandline, expectedline, timeout):
		logging.debug(commandline)
		self.ssh.timeout = timeout
		self.ssh.sendline(commandline)
		self.sshresponse = self.ssh.expect([expectedline, pexpect.EOF, pexpect.TIMEOUT])
		if self.sshresponse == 0:
			pass
		elif self.sshresponse == 1:
			logging.debug('\u001B[1;37;41m Unexpected EOF \u001B[0m')
			logging.debug('Expected Line : ' + expectedline)
			sys.exit(self.sshresponse)
		elif self.sshresponse == 2:
			logging.debug('\u001B[1;37;41m Unexpected TIMEOUT \u001B[0m')
			logging.debug('Expected Line : ' + expectedline)
			sys.exit(self.sshresponse)
		else:
			logging.debug('\u001B[1;37;41m Unexpected Others \u001B[0m')
			logging.debug('Expected Line : ' + expectedline)
			sys.exit(self.sshresponse)

	def close(self):
		self.ssh.timeout = 5
		self.ssh.sendline('exit')
		self.sshresponse = self.ssh.expect([pexpect.EOF, pexpect.TIMEOUT])
		if self.sshresponse == 0:
			pass
		elif self.sshresponse == 1:
			logging.debug('\u001B[1;37;41m Unexpected TIMEOUT \u001B[0m')
		else:
			logging.debug('\u001B[1;37;41m Unexpected Others \u001B[0m')

	def BuildeNB(self):
		if self.eNBIPAddress == '' or self.eNBRepository == '' or self.eNBBranch == '' or self.eNBUserName == '' or self.eNBPassword == '' or self.eNBSourceCodePath == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
		self.command('mkdir -p ' + self.eNBSourceCodePath, '\$', 5)
		self.command('cd ' + self.eNBSourceCodePath, '\$', 5)
		self.command('if [ ! -e .git ]; then stdbuf -o0 git clone ' + self.eNBRepository + ' .; else stdbuf -o0 git fetch; fi', '\$', 600)
		# Raphael: here add a check if git clone or git fetch went smoothly
		self.command('git config user.email "jenkins@openairinterface.org"', '\$', 5)
		self.command('git config user.name "OAI Jenkins"', '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S git clean -x -d -ff', '\$', 30)
		# if the commit ID is provided use it to point to it
		if self.eNBCommitID != '':
			self.command('git checkout -f ' + self.eNBCommitID, '\$', 5)
		# if the branch is not develop, then it is a merge request and we need to do 
		# the potential merge. Note that merge conflicts should already been checked earlier
		if (self.eNBBranch != 'develop') and (self.eNBBranch != 'origin/develop'):
			self.command('git merge --ff origin/develop -m "Temporary merge for CI"', '\$', 5)
		self.command('source oaienv', '\$', 5)
		self.command('cd cmake_targets', '\$', 5)
		self.command('mkdir -p  log', '\$', 5)
		# no need to remove in log (git clean did the trick)
		self.command('echo ' + self.eNBPassword + ' | sudo -S stdbuf -o0 ./build_oai ' + self.Build_eNB_args + ' 2>&1 | stdbuf -o0 tee -a compile_oai_enb.log', 'Bypassing the Tests', 600)
		self.command('mkdir -p build_log_' + SSH.testCase_id, '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S mv log/* ' + 'build_log_' + SSH.testCase_id, '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S mv compile_oai_enb.log ' + 'build_log_' + SSH.testCase_id, '\$', 5)
		self.close()

	def InitializeHSS(self):
		if self.EPCIPAddress == '' or self.EPCUserName == '' or self.EPCPassword == '' or self.EPCSourceCodePath == '' or self.EPCType == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			logging.debug('Using the OAI EPC HSS')
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('source oaienv', '\$', 5)
			self.command('cd scripts', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./run_hss 2>&1 | stdbuf -o0 awk \'{ print strftime("[%Y/%m/%d %H:%M:%S] ",systime()) $0 }\' | stdbuf -o0 tee -a hss_' + SSH.testCase_id + '.log &', 'Core state: 2 -> 3', 35)
		else:
			logging.debug('Using the ltebox simulated HSS')
			self.command('if [ -d ' + self.EPCSourceCodePath + '/scripts ]; then echo ' + self.eNBPassword + ' | sudo -S rm -Rf ' + self.EPCSourceCodePath + '/scripts ; fi', '\$', 5)
			self.command('mkdir -p ' + self.EPCSourceCodePath + '/scripts', '\$', 5)
			self.command('cd /opt/hss_sim0609', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S rm -f hss.log daemon.log', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S echo "Starting sudo session" && sudo daemon --unsafe --name=simulated_hss --chdir=/opt/hss_sim0609 ./starthss_real  ', '\$', 5)
		self.close()

	def InitializeMME(self):
		if self.EPCIPAddress == '' or self.EPCUserName == '' or self.EPCPassword == '' or self.EPCSourceCodePath == '' or self.EPCType == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('source oaienv', '\$', 5)
			self.command('cd scripts', '\$', 5)
			self.command('stdbuf -o0 hostname', '\$', 5)
			result = re.search('hostname\\\\r\\\\n(?P<host_name>[a-zA-Z0-9\-\_]+)\\\\r\\\\n', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m Hostname Not Found! \u001B[0m')
				sys.exit(1)
			host_name = result.group('host_name')
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./run_mme 2>&1 | stdbuf -o0 tee -a mme_' + SSH.testCase_id + '.log &', 'MME app initialization complete', 100)
		else:
			self.command('cd /opt/ltebox/tools', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./start_mme', '\$', 5)
		self.close()

	def InitializeSPGW(self):
		if self.EPCIPAddress == '' or self.EPCUserName == '' or self.EPCPassword == '' or self.EPCSourceCodePath == '' or self.EPCType == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('source oaienv', '\$', 5)
			self.command('cd scripts', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./run_spgw 2>&1 | stdbuf -o0 tee -a spgw_' + SSH.testCase_id + '.log &', 'Initializing SPGW-APP task interface: DONE', 30)
		else:
			self.command('cd /opt/ltebox/tools', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./start_xGw', '\$', 5)
		self.close()

	def InitializeeNB(self):
		if self.eNBIPAddress == '' or self.eNBUserName == '' or self.eNBPassword == '' or self.eNBSourceCodePath == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = True
		self.CheckProcessExist(initialize_eNB_flag)
		self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
		self.command('cd ' + self.eNBSourceCodePath, '\$', 5)
		# Initialize_eNB_args usually start with -O and followed by the location in repository
		full_config_file = self.Initialize_eNB_args.replace('-O ','')
		config_path, config_file = os.path.split(full_config_file)
		ci_full_config_file = config_path + '/ci-' + config_file
		# Make a copy and adapt to EPC / eNB IP addresses
		self.command('cp ' + full_config_file + ' ' + ci_full_config_file, '\$', 5)
		self.command('sed -i -e \'s/mme_ip_address.*$/mme_ip_address      = ( { ipv4       = "' + self.EPCIPAddress + '";/\' ' + ci_full_config_file, '\$', 2);
		self.command('sed -i -e \'s/ENB_IPV4_ADDRESS_FOR_S1_MME.*$/ENB_IPV4_ADDRESS_FOR_S1_MME              = "' + self.eNBIPAddress + '";/\' ' + ci_full_config_file, '\$', 2);
		self.command('sed -i -e \'s/ENB_IPV4_ADDRESS_FOR_S1U.*$/ENB_IPV4_ADDRESS_FOR_S1U                 = "' + self.eNBIPAddress + '";/\' ' + ci_full_config_file, '\$', 2);
		# Launch eNB with the modified config file
		self.command('source oaienv', '\$', 5)
		self.command('cd cmake_targets', '\$', 5)
		self.command('echo "./lte_build_oai/build/lte-softmodem -O ' + self.eNBSourceCodePath + '/' + ci_full_config_file + '" > ./my-lte-softmodem-run.sh ', '\$', 5)
		self.command('chmod 775 ./my-lte-softmodem-run.sh ', '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S -E daemon --inherit --unsafe --name=enb_daemon --chdir=' + self.eNBSourceCodePath + '/cmake_targets -o ' + self.eNBSourceCodePath + '/cmake_targets/enb_' + SSH.testCase_id + '.log ./my-lte-softmodem-run.sh', '\$', 5)
		time.sleep(6)
		doLoop = True
		loopCounter = 10
		while (doLoop):
			loopCounter = loopCounter - 1
			if (loopCounter == 0):
				doLoop = False
				logging.debug('\u001B[1;37;41m Starting eNB Failed -- taking too much time \u001B[0m')
				sys.exit(1)
			self.command('stdbuf -o0 cat enb_' + SSH.testCase_id + '.log', '\$', 10)
			result = re.search('got sync', str(self.ssh.before))
			if result is None:
				time.sleep(6)
			else:
				doLoop = False
				logging.debug('\u001B[1m Initialize eNB Completed\u001B[0m')

		self.close()

	def InitializeUE_common(self, device_id):
		logging.debug('send adb commands')
		try:
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			# The following commands are deprecated since we no longer work on Android 7+
			# self.command('stdbuf -o0 adb -s ' + device_id + ' shell settings put global airplane_mode_on 1', '\$', 10)
			# self.command('stdbuf -o0 adb -s ' + device_id + ' shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true', '\$', 60)
			# a dedicated script has to be installed inside the UE
			# airplane mode on means call /data/local/tmp/off
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/off', '\$', 60)
			#airplane mode off means call /data/local/tmp/on
			logging.debug('\u001B[1mUE (' + device_id + ') Initialize Completed\u001B[0m')
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def InitializeUE(self):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		multi_jobs = []
		for device_id in self.UEDevices:
			p = Process(target = SSH.InitializeUE_common, args = (device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def AttachUE_common(self, device_id):
		try:
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/on', '\$', 60)
			time.sleep(2)
			count = 45
			while count > 0:
				self.command('stdbuf -o0 adb -s ' + device_id + ' shell dumpsys telephony.registry | grep mDataConnectionState', '\$', 15)
				result = re.search('mDataConnectionState.*=(?P<state>[0-9\-]+)', str(self.ssh.before))
				if result is None:
					logging.debug('\u001B[1;37;41m mDataConnectionState Not Found! \u001B[0m')
					sys.exit(1)
				mDataConnectionState = int(result.group('state'))
				if mDataConnectionState == 2:
					logging.debug('\u001B[1mUE (' + device_id + ') Attach Completed\u001B[0m')
					break
				count = count - 1
				if count == 15 or count == 30:
					logging.debug('\u001B[1;37;43m Retry UE (' + device_id + ') Flight Mode Off \u001B[0m')
					self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/off', '\$', 60)
					time.sleep(0.5)
					self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/on', '\$', 60)
					time.sleep(0.5)
				logging.debug('\u001B[1mWait UE (' + device_id + ') a second until mDataConnectionState=2 (' + str(45-count) + ' times)\u001B[0m')
				time.sleep(1)
			if count == 0:
				logging.debug('\u001B[1;37;41m UE (' + device_id + ') Attach Failed \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def AttachUE(self):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = False
		self.CheckProcessExist(initialize_eNB_flag)
		multi_jobs = []
		for device_id in self.UEDevices:
			p = Process(target = SSH.AttachUE_common, args = (device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def DetachUE_common(self, device_id):
		try:
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/off', '\$', 60)
			logging.debug('\u001B[1mUE (' + device_id + ') Detach Completed\u001B[0m')
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def DetachUE(self):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = False
		self.CheckProcessExist(initialize_eNB_flag)
		multi_jobs = []
		for device_id in self.UEDevices:
			p = Process(target = SSH.DetachUE_common, args = (device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def RebootUE_common(self, device_id):
		try:
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			previousmDataConnectionStates = []
			# Save mDataConnectionState
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell dumpsys telephony.registry | grep mDataConnectionState', '\$', 15)
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell dumpsys telephony.registry | grep mDataConnectionState', '\$', 15)
			result = re.search('mDataConnectionState.*=(?P<state>[0-9\-]+)', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m mDataConnectionState Not Found! \u001B[0m')
				sys.exit(1)
			previousmDataConnectionStates.append(int(result.group('state')))
			# Reboot UE
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell reboot', '\$', 10)
			time.sleep(60)
			previousmDataConnectionState = previousmDataConnectionStates.pop(0)
			count = 180
			while count > 0:
				count = count - 1
				self.command('stdbuf -o0 adb -s ' + device_id + ' shell dumpsys telephony.registry | grep mDataConnectionState', '\$', 15)
				result = re.search('mDataConnectionState.*=(?P<state>[0-9\-]+)', str(self.ssh.before))
				if result is None:
					mDataConnectionState = None
				else:
					mDataConnectionState = int(result.group('state'))
					logging.debug('mDataConnectionState = ' + result.group('state'))
				if mDataConnectionState is None or (previousmDataConnectionState == 2 and mDataConnectionState != 2):
					logging.debug('\u001B[1mWait UE (' + device_id + ') a second until reboot completion (' + str(180-count) + ' times)\u001B[0m')
					time.sleep(1)
				else:
					logging.debug('\u001B[1mUE (' + device_id + ') Reboot Completed\u001B[0m')
					break
			if count == 0:
				logging.debug('\u001B[1;37;41m UE (' + device_id + ') Reboot Failed \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def RebootUE(self):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = False
		self.CheckProcessExist(initialize_eNB_flag)
		multi_jobs = []
		for device_id in self.UEDevices:
			p = Process(target = SSH.RebootUE_common, args = (device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def GetAllUEDevices(self, terminate_ue_flag):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
		self.command('adb devices', '\$', 15)
		self.UEDevices = re.findall("\\\\r\\\\n([A-Za-z0-9]+)\\\\tdevice",str(self.ssh.before))
		if terminate_ue_flag == False:
			if len(self.UEDevices) == 0:
				logging.debug('\u001B[1;37;41m UE Not Found! \u001B[0m')
				sys.exit(1)
		self.close()

	def GetAllUEIPAddresses(self):
		if self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		self.UEIPAddresses = []
		self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
		for device_id in self.UEDevices:
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell ip addr show | grep rmnet', '\$', 15)
			result = re.search('inet (?P<ueipaddress>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\/[0-9]+[0-9a-zA-Z\.\s]+', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m UE IP Address Not Found! \u001B[0m')
				sys.exit(1)
			UE_IPAddress = result.group('ueipaddress')
			logging.debug('\u001B[1mUE (' + device_id + ') IP Address is ' + UE_IPAddress + '\u001B[0m')
			for ueipaddress in self.UEIPAddresses:
				if ueipaddress == UE_IPAddress:
					logging.debug('\u001B[1mUE (' + device_id + ') IP Address ' + UE_IPAddress + 'has been existed!' + '\u001B[0m')
					sys.exit(1)
			self.UEIPAddresses.append(UE_IPAddress)
		self.close()

	def Ping_common(self, lock, UE_IPAddress, device_id):
		try:
			self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('cd scripts', '\$', 5)
			ping_time = re.findall("-c (\d+)",str(self.ping_args))
			self.command('stdbuf -o0 ping ' + self.ping_args + ' ' + UE_IPAddress + ' 2>&1 | stdbuf -o0 tee -a ping_' + SSH.testCase_id + '_' + device_id + '.log', '\$', int(ping_time[0])*1.5)
			result = re.search(', (?P<packetloss>[0-9\.]+)% packet loss, time [0-9\.]+ms', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m Packet Loss Not Found! \u001B[0m')
				sys.exit(1)
			packetloss = result.group('packetloss')
			if float(packetloss) == 100:
				logging.debug('\u001B[1;37;41m Packet Loss is 100% \u001B[0m')
				sys.exit(1)
			result = re.search('rtt min\/avg\/max\/mdev = (?P<rtt_min>[0-9\.]+)\/(?P<rtt_avg>[0-9\.]+)\/(?P<rtt_max>[0-9\.]+)\/[0-9\.]+ ms', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m Ping RTT_Min RTT_Avg RTT_Max Not Found! \u001B[0m')
				sys.exit(1)
			rtt_min = result.group('rtt_min')
			rtt_avg = result.group('rtt_avg')
			rtt_max = result.group('rtt_max')
			lock.acquire()
			logging.debug('\u001B[1;37;44m ping result (' + UE_IPAddress + ') \u001B[0m')
			logging.debug('\u001B[1;34m    Packet Loss : ' + packetloss + '%\u001B[0m')
			logging.debug('\u001B[1;34m    RTT(Min)    : ' + rtt_min + ' ms' + '\u001B[0m')
			logging.debug('\u001B[1;34m    RTT(Avg)    : ' + rtt_avg + ' ms' + '\u001B[0m')
			logging.debug('\u001B[1;34m    RTT(Max)    : ' + rtt_max + ' ms' + '\u001B[0m')
			lock.release()
			if packetloss is not None:
				if float(packetloss) > float(self.ping_packetloss_threshold):
					logging.debug('\u001B[1;37;41m Packet Loss too high \u001B[0m')
					sys.exit(1)
				elif float(packetloss) > 0:
					logging.debug('\u001B[1;37;43m Packet Loss is not 0% \u001B[0m')
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def Ping(self):
		if self.EPCIPAddress == '' or self.EPCUserName == '' or self.EPCPassword == '' or self.EPCSourceCodePath == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = False
		self.CheckProcessExist(initialize_eNB_flag)
		self.GetAllUEIPAddresses()
		multi_jobs = []
		i = 0
		lock = Lock()
		for UE_IPAddress in self.UEIPAddresses:
			device_id = self.UEDevices[i]
			p = Process(target = SSH.Ping_common, args = (lock,UE_IPAddress,device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
			i = i + 1
		for job in multi_jobs:
			job.join()

	def Iperf_common(self, lock, UE_IPAddress, device_id, ue_num):
		try:
			useIperf3 = False
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			# Checking if iperf / iperf3 are installed
			self.command('adb -s ' + device_id + ' shell "ls /data/local/tmp"', '\$', 5)
			result = re.search('iperf3', str(self.ssh.before))
			if result is None:
				result = re.search('iperf', str(self.ssh.before))
				if result is None:
					logging.debug('\u001B[1;37;41m Neither iperf nor iperf3 installed on UE! \u001B[0m')
					sys.exit(1)
			else:
				useIperf3 = True
			if (useIperf3):
				self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/iperf3 -s &', '\$', 5)
			else:
				self.command('rm -f /tmp/iperf_server_' + SSH.testCase_id + '_' + device_id + '.log', '\$', 5)
				self.command('echo $USER; nohup adb -s ' + device_id + ' shell "/data/local/tmp/iperf -u -s -i 1" > /tmp/iperf_server_' + SSH.testCase_id + '_' + device_id + '.log &', self.ADBUserName, 5)
			time.sleep(0.5)
			self.close()

			self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('cd scripts', '\$', 5)
			result = re.search('-t (?P<iperf_time>\d+)', str(self.iperf_args))
			if result is None:
				logging.debug('\u001B[1;37;41m Iperf time Not Found! \u001B[0m')
				sys.exit(1)
			iperf_time = result.group('iperf_time')
			time.sleep(0.5)

			result = re.search('-b (?P<iperf_bandwidth>[0-9\.]+)[KMG]', str(self.iperf_args))
			if result is None:
				logging.debug('\u001B[1;37;41m Iperf bandwidth Not Found! \u001B[0m')
				sys.exit(1)
			iperf_bandwidth = result.group('iperf_bandwidth')
			time.sleep(0.5)

			iperf_bandwidth_new = float(iperf_bandwidth)/ue_num
			iperf_bandwidth_str = '-b ' + iperf_bandwidth
			iperf_bandwidth_str_new = '-b ' + str(iperf_bandwidth_new)
			result = re.sub(iperf_bandwidth_str, iperf_bandwidth_str_new, str(self.iperf_args))
			if result is None:
				logging.debug('\u001B[1;37;41m Calculate Iperf bandwidth Failed! \u001B[0m')
				sys.exit(1)

			self.command('rm -f iperf_' + SSH.testCase_id + '_' + device_id + '.log', '\$', 5)
			if (useIperf3):
				self.command('stdbuf -o0 iperf3 -c ' + UE_IPAddress + ' ' + result + ' 2>&1 | stdbuf -o0 tee -a iperf_' + SSH.testCase_id + '_' + device_id + '.log', '\$', int(iperf_time)*5.0)

				result = re.search('(?P<bitrate>[0-9\.]+ [KMG]bits\/sec) +(?:|[0-9\.]+ ms +\d+\/\d+ \((?P<packetloss>[0-9\.]+)%\)) +(?:|receiver)\\\\r\\\\n(?:|\[ *\d+\] Sent \d+ datagrams)\\\\r\\\\niperf Done\.', str(self.ssh.before))
				if result is None:
					result = re.search('(?P<error>iperf: error - [a-zA-Z0-9 :]+)', str(self.ssh.before))
					if result is not None:
						logging.debug('\u001B[1;37;41m ' + result.group('error') + ' \u001B[0m')
					else:
						logging.debug('\u001B[1;37;41m Bitrate and/or Packet Loss Not Found! \u001B[0m')
					sys.exit(1)
				bitrate = result.group('bitrate')
				packetloss = result.group('packetloss')
				lock.acquire()
				logging.debug('\u001B[1;37;44m iperf result (' + UE_IPAddress + ') \u001B[0m')
				logging.debug('\u001B[1;34m    Bitrate     : ' + bitrate + '\u001B[0m')
				if packetloss is not None:
					logging.debug('\u001B[1;34m    Packet Loss : ' + packetloss + '%\u001B[0m')
					if float(packetloss) > float(self.iperf_packetloss_threshold):
						logging.debug('\u001B[1;37;41m Packet Loss too high \u001B[0m')
						lock.release()
						sys.exit(1)
				lock.release()
			else:
				self.command('stdbuf -o0 iperf -c ' + UE_IPAddress + ' ' + result + ' 2>&1 | stdbuf -o0 tee -a iperf_' + SSH.testCase_id + '_' + device_id + '.log', '\$', int(iperf_time)*5.0)

				result = re.search('Server Report:', str(self.ssh.before))
				if result is None:
					result = re.search('read failed: Connection refused', str(self.ssh.before))
					if result is not None:
						logging.debug('\u001B[1;37;41m Could not connect to iperf server! \u001B[0m')
					else:
						logging.debug('\u001B[1;37;41m Server Report and Connection refused Not Found! \u001B[0m')
					sys.exit(1)
				result = re.search('Server Report:\\\\r\\\\n(?:|\[ *\d+\].*) (?P<bitrate>[0-9\.]+ [KMG]bits\/sec) +(?:|[0-9\.]+ ms +\d+\/\d+ \((?P<packetloss>[0-9\.]+)%\))', str(self.ssh.before))
				if result is not None:
					bitrate = result.group('bitrate')
					packetloss = result.group('packetloss')
					lock.acquire()
					logging.debug('\u001B[1;37;44m iperf result (' + UE_IPAddress + ') \u001B[0m')
					if bitrate is not None:
						logging.debug('\u001B[1;34m    Bitrate     : ' + bitrate + '\u001B[0m')
					if packetloss is not None:
						logging.debug('\u001B[1;34m    Packet Loss : ' + packetloss + '%\u001B[0m')
						if float(packetloss) > float(self.iperf_packetloss_threshold):
							logging.debug('\u001B[1;37;41m Packet Loss too high \u001B[0m')
							lock.release()
							sys.exit(1)
					lock.release()
			self.close()

			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell ps | grep --color=never iperf | grep -v grep', '\$', 5)
			result = re.search('shell +(?P<pid>\d+)', str(self.ssh.before))
			if result is not None:
				pid_iperf = result.group('pid')
				self.command('stdbuf -o0 adb -s ' + device_id + ' shell kill -KILL ' + pid_iperf, '\$', 5)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def Iperf(self):
		if self.EPCIPAddress == '' or self.EPCUserName == '' or self.EPCPassword == '' or self.EPCSourceCodePath == '' or self.ADBIPAddress == '' or self.ADBUserName == '' or self.ADBPassword == '':
			Usage()
			sys.exit('Insufficient Parameter')
		initialize_eNB_flag = False
		self.CheckProcessExist(initialize_eNB_flag)
		self.GetAllUEIPAddresses()
		multi_jobs = []
		i = 0
		ue_num = len(self.UEIPAddresses)
		lock = Lock()
		for UE_IPAddress in self.UEIPAddresses:
			device_id = self.UEDevices[i]
			p = Process(target = SSH.Iperf_common, args = (lock,UE_IPAddress,device_id,ue_num,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
			i = i + 1
		for job in multi_jobs:
			job.join()

	def CheckProcessExist(self, initialize_eNB_flag):
		multi_jobs = []
		p = Process(target = SSH.CheckHSSProcess, args = ())
		p.daemon = True
		p.start()
		multi_jobs.append(p)
		p = Process(target = SSH.CheckMMEProcess, args = ())
		p.daemon = True
		p.start()
		multi_jobs.append(p)
		p = Process(target = SSH.CheckSPGWProcess, args = ())
		p.daemon = True
		p.start()
		multi_jobs.append(p)
		if initialize_eNB_flag == False:
			p = Process(target = SSH.CheckeNBProcess, args = ())
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def CheckeNBProcess(self):
		try:
			self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
			self.command('stdbuf -o0 ps -aux | grep -v grep | grep --color=never lte-softmodem', '\$', 5)
			result = re.search('lte-softmodem', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m eNB Process Not Found! \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def CheckHSSProcess(self):
		try:
			self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
			self.command('stdbuf -o0 ps -aux | grep -v grep | grep --color=never hss', '\$', 5)
			if re.match('OAI', self.EPCType, re.IGNORECASE):
				result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			else:
				result = re.search('hss_sim s6as diam_hss', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m HSS Process Not Found! \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def CheckMMEProcess(self):
		try:
			self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
			self.command('stdbuf -o0 ps -aux | grep -v grep | grep --color=never mme', '\$', 5)
			if re.match('OAI', self.EPCType, re.IGNORECASE):
				result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			else:
				result = re.search('mme', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m MME Process Not Found! \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def CheckSPGWProcess(self):
		try:
			self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
			if re.match('OAI', self.EPCType, re.IGNORECASE):
				self.command('stdbuf -o0 ps -aux | grep -v grep | grep --color=never spgw', '\$', 5)
				result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			else:
				self.command('stdbuf -o0 ps -aux | grep -v grep | grep --color=never xGw', '\$', 5)
				result = re.search('xGw', str(self.ssh.before))
			if result is None:
				logging.debug('\u001B[1;37;41m SPGW Process Not Found! \u001B[0m')
				sys.exit(1)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def TerminateeNB(self):
		self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
		self.command('cd ' + self.eNBSourceCodePath + '/cmake_targets', '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S daemon --name=enb_daemon --stop', '\$', 5)
		self.command('rm -f my-lte-softmodem-run.sh', '\$', 5)
		self.command('echo ' + self.eNBPassword + ' | sudo -S killall --signal SIGINT lte-softmodem || true', '\$', 5)
		time.sleep(5)
		self.command('stdbuf -o0  ps -aux | grep -v grep | grep lte-softmodem', '\$', 5)
		result = re.search('lte-softmodem', str(self.ssh.before))
		if result is not None:
			self.command('echo ' + self.eNBPassword + ' | sudo -S killall --signal SIGKILL lte-softmodem || true', '\$', 5)
		self.close()

	def TerminateHSS(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGINT run_hss oai_hss || true', '\$', 5)
			time.sleep(2)
			self.command('stdbuf -o0  ps -aux | grep -v grep | grep hss', '\$', 5)
			result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			if result is not None:
				self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGKILL run_hss oai_hss || true', '\$', 5)
		else:
			self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
			self.command('cd scripts', '\$', 5)
			self.command('rm -f ./kill_hss.sh', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S daemon --name=simulated_hss --stop', '\$', 5)
			time.sleep(2)
			self.command('ps -aux | egrep --color=never "hss_sim|simulated_hss" | grep -v grep | awk \'BEGIN{n=0}{pidId[n]=$2;n=n+1}END{print "kill -9 " pidId[0] " " pidId[1]}\' > ./kill_hss.sh', '\$', 5)
			self.command('chmod 755 ./kill_hss.sh', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./kill_hss.sh', '\$', 5)
			self.command('rm ./kill_hss.sh', '\$', 5)
		self.close()

	def TerminateMME(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGINT run_mme mme || true', '\$', 5)
			time.sleep(2)
			self.command('stdbuf -o0 ps -aux | grep -v grep | grep mme', '\$', 5)
			result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			if result is not None:
				self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGKILL run_mme mme || true', '\$', 5)
		else:
			self.command('cd /opt/ltebox/tools', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./stop_mme', '\$', 5)
		self.close()

	def TerminateSPGW(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGINT run_spgw spgw || true', '\$', 5)
			time.sleep(2)
			self.command('stdbuf -o0 ps -aux | grep -v grep | grep spgw', '\$', 5)
			result = re.search('\/bin\/bash .\/run_', str(self.ssh.before))
			if result is not None:
				self.command('echo ' + self.EPCPassword + ' | sudo -S killall --signal SIGKILL run_spgw spgw || true', '\$', 5)
		else:
			self.command('cd /opt/ltebox/tools', '\$', 5)
			self.command('echo ' + self.EPCPassword + ' | sudo -S ./stop_xGw', '\$', 5)
		self.close()

	def TerminateUE_common(self, device_id):
		try:
			self.open(self.ADBIPAddress, self.ADBUserName, self.ADBPassword)
			self.command('stdbuf -o0 adb -s ' + device_id + ' shell /data/local/tmp/off', '\$', 60)
			logging.debug('\u001B[1mUE (' + device_id + ') Detach Completed\u001B[0m')

			self.command('stdbuf -o0 adb -s ' + device_id + ' shell ps | grep --color=never iperf | grep -v grep', '\$', 5)
			result = re.search('shell +(?P<pid>\d+)', str(self.ssh.before))
			if result is not None:
				pid_iperf = result.group('pid')
				self.command('stdbuf -o0 adb -s ' + device_id + ' shell kill -KILL ' + pid_iperf, '\$', 5)
			self.close()
		except:
			os.kill(os.getppid(),signal.SIGUSR1)

	def TerminateUE(self):
		terminate_ue_flag = True
		SSH.GetAllUEDevices(terminate_ue_flag)
		multi_jobs = []
		for device_id in self.UEDevices:
			p = Process(target= SSH.TerminateUE_common, args = (device_id,))
			p.daemon = True
			p.start()
			multi_jobs.append(p)
		for job in multi_jobs:
			job.join()

	def LogCollectBuild(self):
		self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
		self.command('cd ' + self.eNBSourceCodePath, '\$', 5)
		self.command('cd cmake_targets', '\$', 5)
		self.command('zip build.log.zip build_log_*/*', '\$', 60)
		self.command('rm -rf build_log_*', '\$', 5)
		self.close()

	def LogCollecteNB(self):
		self.open(self.eNBIPAddress, self.eNBUserName, self.eNBPassword)
		self.command('cd ' + self.eNBSourceCodePath, '\$', 5)
		self.command('cd cmake_targets', '\$', 5)
		self.command('zip enb.log.zip enb*.log', '\$', 60)
		self.command('rm enb*.log', '\$', 5)
		self.close()

	def LogCollectPing(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
		self.command('cd scripts', '\$', 5)
		self.command('zip ping.log.zip ping*.log', '\$', 60)
		self.command('rm ping*.log', '\$', 5)
		self.close()

	def LogCollectIperf(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
		self.command('cd scripts', '\$', 5)
		self.command('zip iperf.log.zip iperf*.log', '\$', 60)
		self.command('rm iperf*.log', '\$', 5)
		self.close()

	def LogCollectHSS(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
		self.command('cd scripts', '\$', 5)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('zip hss.log.zip hss*.log', '\$', 60)
			self.command('rm hss*.log', '\$', 5)
		else:
			self.command('cp /opt/hss_sim0609/hss.log .', '\$', 60)
			self.command('zip hss.log.zip hss.log', '\$', 60)
		self.close()

	def LogCollectMME(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
		self.command('cd scripts', '\$', 5)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('zip mme.log.zip mme*.log', '\$', 60)
			self.command('rm mme*.log', '\$', 5)
		else:
			self.command('cp /opt/ltebox/var/log/*Log.0 .', '\$', 5)
			self.command('zip mme.log.zip mmeLog.0 s1apcLog.0 s1apsLog.0 s11cLog.0 libLog.0 s1apCodecLog.0', '\$', 60)
		self.close()

	def LogCollectSPGW(self):
		self.open(self.EPCIPAddress, self.EPCUserName, self.EPCPassword)
		self.command('cd ' + self.EPCSourceCodePath, '\$', 5)
		self.command('cd scripts', '\$', 5)
		if re.match('OAI', self.EPCType, re.IGNORECASE):
			self.command('zip spgw.log.zip spgw*.log', '\$', 60)
			self.command('rm spgw*.log', '\$', 5)
		else:
			self.command('cp /opt/ltebox/var/log/xGwLog.0 .', '\$', 5)
			self.command('zip spgw.log.zip xGwLog.0', '\$', 60)
		self.close()
#-----------------------------------------------------------
# Usage()
#-----------------------------------------------------------
def Usage():
	print('------------------------------------------------------------')
	print('main.py Ver:' + Version)
	print('------------------------------------------------------------')
	print('Usage: python main.py [options]')
	print('  --help  Show this help.')
	print('  --mode=[Mode]')
	print('      TesteNB')
	print('      TerminateeNB, TerminateEPC')
	print('      LogCollectBuild, LogCollecteNB, LogCollectEPC, LogCollectADB')
	print('  --eNBIPAddress=[eNB\'s IP Address]')
	print('  --eNBRepository=[eNB\'s Repository URL]')
	print('  --eNBBranch=[eNB\'s Branch Name]')
	print('  --eNBCommitID=[eNB\'s Commit Number]')
	print('  --eNBUserName=[eNB\'s Login User Name]')
	print('  --eNBPassword=[eNB\'s Login Password]')
	print('  --eNBSourceCodePath=[eNB\'s Source Code Path]')
	print('  --EPCIPAddress=[EPC\'s IP Address]')
	print('  --EPCUserName=[EPC\'s Login User Name]')
	print('  --EPCPassword=[EPC\'s Login Password]')
	print('  --EPCSourceCodePath=[EPC\'s Source Code Path]')
	print('  --EPCType=[EPC\'s Type: OAI or ltebox]')
	print('  --ADBIPAddress=[ADB\'s IP Address]')
	print('  --ADBUserName=[ADB\'s Login User Name]')
	print('  --ADBPassword=[ADB\'s Login Password]')
	print('  --XMLTestFile=[XML Test File to be run]')
	print('------------------------------------------------------------')

#-----------------------------------------------------------
# ShowTestID()
#-----------------------------------------------------------
def ShowTestID():
	logging.debug('\u001B[1m----------------------------------------\u001B[0m')
	logging.debug('\u001B[1mTest ID:' + SSH.testCase_id + '\u001B[0m')
	logging.debug('\u001B[1m' + SSH.desc + '\u001B[0m')
	logging.debug('\u001B[1m----------------------------------------\u001B[0m')

def CheckClassValidity(action,id):
	if action != 'Build_eNB' and action != 'Initialize_eNB' and action != 'Terminate_eNB' and action != 'Initialize_UE' and action != 'Terminate_UE' and action != 'Attach_UE' and action != 'Detach_UE' and action != 'Ping' and action != 'Iperf' and action != 'Reboot_UE' and action != 'Initialize_HSS' and action != 'Terminate_HSS' and action != 'Initialize_MME' and action != 'Terminate_MME' and action != 'Initialize_SPGW' and action != 'Terminate_SPGW':
		logging.debug('ERROR: test-case ' + id + ' has wrong class ' + action)
		return False
	return True

def GetParametersFromXML(action):
	if action == 'Build_eNB':
		SSH.Build_eNB_args = test.findtext('Build_eNB_args')

	if action == 'Initialize_eNB':
		SSH.Initialize_eNB_args = test.findtext('Initialize_eNB_args')

	if action == 'Ping':
		SSH.ping_args = test.findtext('ping_args')
		SSH.ping_packetloss_threshold = test.findtext('ping_packetloss_threshold')

	if action == 'Iperf':
		SSH.iperf_args = test.findtext('iperf_args')
		SSH.iperf_packetloss_threshold = test.findtext('iperf_packetloss_threshold')

#check if given test is in list
#it is in list if one of the strings in 'list' is at the beginning of 'test'
def test_in_list(test, list):
	for check in list:
		check=check.replace('+','')
		if (test.startswith(check)):
			return True
	return False

def receive_signal(signum, frame):
	sys.exit(1)

#-----------------------------------------------------------
# Parameter Check
#-----------------------------------------------------------
mode = ''
SSH = SSHConnection()

argvs = sys.argv
argc = len(argvs)

while len(argvs) > 1:
	myArgv = argvs.pop(1)	# 0th is this file's name
	if re.match('^\-\-help$', myArgv, re.IGNORECASE):
		Usage()
		sys.exit(0)
	elif re.match('^\-\-mode=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-mode=(.+)$', myArgv, re.IGNORECASE)
		mode = matchReg.group(1)
	elif re.match('^\-\-eNBIPAddress=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBIPAddress=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBIPAddress = matchReg.group(1)
	elif re.match('^\-\-eNBRepository=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBRepository=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBRepository = matchReg.group(1)
	elif re.match('^\-\-eNBBranch=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBBranch=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBBranch = matchReg.group(1)
	elif re.match('^\-\-eNBCommitID=(.*)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBCommitID=(.*)$', myArgv, re.IGNORECASE)
		SSH.eNBCommitID = matchReg.group(1)
	elif re.match('^\-\-eNBUserName=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBUserName=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBUserName = matchReg.group(1)
	elif re.match('^\-\-eNBPassword=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBPassword=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBPassword = matchReg.group(1)
	elif re.match('^\-\-eNBSourceCodePath=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-eNBSourceCodePath=(.+)$', myArgv, re.IGNORECASE)
		SSH.eNBSourceCodePath = matchReg.group(1)
	elif re.match('^\-\-EPCIPAddress=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCIPAddress=(.+)$', myArgv, re.IGNORECASE)
		SSH.EPCIPAddress = matchReg.group(1)
	elif re.match('^\-\-EPCBranch=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCBranch=(.+)$', myArgv, re.IGNORECASE)
		SSH.EPCBranch = matchReg.group(1)
	elif re.match('^\-\-EPCUserName=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCUserName=(.+)$', myArgv, re.IGNORECASE)
		SSH.EPCUserName = matchReg.group(1)
	elif re.match('^\-\-EPCPassword=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCPassword=(.+)$', myArgv, re.IGNORECASE)
		SSH.EPCPassword = matchReg.group(1)
	elif re.match('^\-\-EPCSourceCodePath=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCSourceCodePath=(.+)$', myArgv, re.IGNORECASE)
		SSH.EPCSourceCodePath = matchReg.group(1)
	elif re.match('^\-\-EPCType=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-EPCType=(.+)$', myArgv, re.IGNORECASE)
		if re.match('OAI', matchReg.group(1), re.IGNORECASE) or re.match('ltebox', matchReg.group(1), re.IGNORECASE):
			SSH.EPCType = matchReg.group(1)
		else:
			sys.exit('Invalid EPC Type: ' + matchReg.group(1) + ' -- (should be OAI or ltebox)')
	elif re.match('^\-\-ADBIPAddress=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-ADBIPAddress=(.+)$', myArgv, re.IGNORECASE)
		SSH.ADBIPAddress = matchReg.group(1)
	elif re.match('^\-\-ADBUserName=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-ADBUserName=(.+)$', myArgv, re.IGNORECASE)
		SSH.ADBUserName = matchReg.group(1)
	elif re.match('^\-\-ADBPassword=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-ADBPassword=(.+)$', myArgv, re.IGNORECASE)
		SSH.ADBPassword = matchReg.group(1)
	elif re.match('^\-\-XMLTestFile=(.+)$', myArgv, re.IGNORECASE):
		matchReg = re.match('^\-\-XMLTestFile=(.+)$', myArgv, re.IGNORECASE)
		SSH.testXMLfile = matchReg.group(1)
	else:
		Usage()
		sys.exit('Invalid Parameter: ' + myArgv)

if re.match('^TerminateeNB$', mode, re.IGNORECASE):
	if SSH.eNBIPAddress == '' or SSH.eNBUserName == '' or SSH.eNBPassword == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.TerminateeNB()
elif re.match('^TerminateUE$', mode, re.IGNORECASE):
	if SSH.ADBIPAddress == '' or SSH.ADBUserName == '' or SSH.ADBPassword == '':
		Usage()
		sys.exit('Insufficient Parameter')
	signal.signal(signal.SIGUSR1, receive_signal)
	SSH.TerminateUE()
elif re.match('^TerminateHSS$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.TerminateHSS()
elif re.match('^TerminateMME$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.TerminateMME()
elif re.match('^TerminateSPGW$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.TerminateSPGW()
elif re.match('^LogCollectBuild$', mode, re.IGNORECASE):
	if SSH.eNBIPAddress == '' or SSH.eNBUserName == '' or SSH.eNBPassword == '' or SSH.eNBSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectBuild()
elif re.match('^LogCollecteNB$', mode, re.IGNORECASE):
	if SSH.eNBIPAddress == '' or SSH.eNBUserName == '' or SSH.eNBPassword == '' or SSH.eNBSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollecteNB()
elif re.match('^LogCollectHSS$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectHSS()
elif re.match('^LogCollectMME$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectMME()
elif re.match('^LogCollectSPGW$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectSPGW()
elif re.match('^LogCollectPing$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectPing()
elif re.match('^LogCollectIperf$', mode, re.IGNORECASE):
	if SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCSourceCodePath == '':
		Usage()
		sys.exit('Insufficient Parameter')
	SSH.LogCollectIperf()
elif re.match('^TesteNB$', mode, re.IGNORECASE):
	if SSH.eNBIPAddress == '' or SSH.eNBRepository == '' or SSH.eNBBranch == '' or SSH.eNBUserName == '' or SSH.eNBPassword == '' or SSH.eNBSourceCodePath == '' or SSH.EPCIPAddress == '' or SSH.EPCUserName == '' or SSH.EPCPassword == '' or SSH.EPCType == '' or SSH.EPCSourceCodePath == '' or SSH.ADBIPAddress == '' or SSH.ADBUserName == '' or SSH.ADBPassword == '':
		Usage()
		sys.exit('Insufficient Parameter')

	#read test_case_list.xml file
        # if no parameters for XML file, use default value
	if SSH.testXMLfile == '':
		xml_test_file = sys.path[0] + "/test_case_list.xml"
	else:
		xml_test_file = sys.path[0] + "/" + SSH.testXMLfile

	xmlTree = ET.parse(xml_test_file)
	xmlRoot = xmlTree.getroot()

	exclusion_tests=xmlRoot.findtext('TestCaseExclusionList',default='')
	requested_tests=xmlRoot.findtext('TestCaseRequestedList',default='')
	all_tests=xmlRoot.findall('testCase')

	exclusion_tests=exclusion_tests.split()
	requested_tests=requested_tests.split()

	#check that exclusion tests are well formatted
	#(6 digits or less than 6 digits followed by +)
	for test in exclusion_tests:
		if     (not re.match('^[0-9]{6}$', test) and
				not re.match('^[0-9]{1,5}\+$', test)):
			logging.debug('ERROR: exclusion test is invalidly formatted: ' + test)
			sys.exit(1)
		else:
			logging.debug(test)

	#check that requested tests are well formatted
	#(6 digits or less than 6 digits followed by +)
	#be verbose
	for test in requested_tests:
		if     (re.match('^[0-9]{6}$', test) or
				re.match('^[0-9]{1,5}\+$', test)):
			logging.debug('INFO: test group/case requested: ' + test)
		else:
			logging.debug('ERROR: requested test is invalidly formatted: ' + test)
			sys.exit(1)

	#get the list of tests to be done
	todo_tests=[]
	for test in requested_tests:
		if    (test_in_list(test, exclusion_tests)):
			logging.debug('INFO: test will be skipped: ' + test)
		else:
			#logging.debug('INFO: test will be run: ' + test)
			todo_tests.append(test)

	signal.signal(signal.SIGUSR1, receive_signal)

	for test_case_id in todo_tests:
		for test in all_tests:
			id = test.get('id')
			if test_case_id != id:
				continue
			SSH.testCase_id = id
			SSH.desc = test.findtext('desc')
			action = test.findtext('class')
			if (CheckClassValidity(action, id) == False):
				continue
			ShowTestID()
			GetParametersFromXML(action)
			if action == 'Initialize_UE' or action == 'Attach_UE' or action == 'Detach_UE' or action == 'Ping' or action == 'Iperf' or action == 'Reboot_UE':
				terminate_ue_flag = False
				SSH.GetAllUEDevices(terminate_ue_flag)
			if action == 'Build_eNB':
				SSH.BuildeNB()
			elif action == 'Initialize_eNB':
				SSH.InitializeeNB()
			elif action == 'Terminate_eNB':
				SSH.TerminateeNB()
			elif action == 'Initialize_UE':
				SSH.InitializeUE()
			elif action == 'Terminate_UE':
				SSH.TerminateUE()
			elif action == 'Attach_UE':
				SSH.AttachUE()
			elif action == 'Detach_UE':
				SSH.DetachUE()
			elif action == 'Ping':
				SSH.Ping()
			elif action == 'Iperf':
				SSH.Iperf()
			elif action == 'Reboot_UE':
				SSH.RebootUE()
			elif action == 'Initialize_HSS':
				SSH.InitializeHSS()
			elif action == 'Terminate_HSS':
				SSH.TerminateHSS()
			elif action == 'Initialize_MME':
				SSH.InitializeMME()
			elif action == 'Terminate_MME':
				SSH.TerminateMME()
			elif action == 'Initialize_SPGW':
				SSH.InitializeSPGW()
			elif action == 'Terminate_SPGW':
				SSH.TerminateSPGW()
			else:
				sys.exit('Invalid action')
else:
	Usage()
	sys.exit('Invalid mode')
sys.exit(0)