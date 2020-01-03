SHELL=/bin/bash

orderer-raft-up:
	python init-orderer-raft.py default

orderer-down:
	python destroy-orderers.py default

peer-up:
	python init-peers.py default
