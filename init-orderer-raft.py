#!/usr/bin/env python

import yaml
import os
import sys
import time

def puts(str):
  print "\033[94m%s\033[0m" %str
  return

namespace = sys.argv[1] if len(sys.argv) > 1 is not None else "orderers"
puts("using %s as namespace ..." %namespace)

def set_orderer_pvc(specs, orderer, domain):
  cmd = ("helm install --name=%s-pvc ./orderer-pvc --namespace=%s"
    " --set domain=%s" %(domain, namespace, domain)
  )
  res = os.system(cmd)
  if res != 0:
    return
  puts("INFO: Copying Configs in orderer PVC")
  create_dir_in_pod(domain)
  ordererDir = "%s-%s" %(specs['Hostname'], orderer['Domain'])
  copy_certs(domain, orderer['Domain'], 'msp', ordererDir)
  copy_certs(domain, orderer['Domain'], 'tls', ordererDir)
  copy_genesis(domain, specs['Hostname'])
  puts("INFO: Configs Copied!! Deleting Test pod")
  os.system("kubectl delete pod %s-injector-pod --namespace=%s" %(domain, namespace))

def create_orderer_pod(domain):
  puts("INFO: Creating orderer pod")
  env = ("--set domain=%s" %(domain))
  cmd = "helm install --name=%s ./orderer --namespace=%s %s" %(domain, namespace, env)
  return os.system(cmd)

def copy_certs(domain, ordDomain, subPath, ordererDir):
  remotePath = "%s/%s-injector-pod:/var/hyperledger/orderer" %(namespace, domain)
  src = "./crypto-config/ordererOrganizations/%s/orderers/%s/%s" %(ordDomain, ordererDir, subPath)
  os.system("kubectl cp %s %s" %(src, remotePath))
  return

def copy_genesis(domain, hostname):
  # rename genesis block
  if (os.path.isfile('./channel-artifacts/genesis.block')):
    remote = "%s/%s-injector-pod:/var/hyperledger/orderer" %(namespace, domain)
    os.system("kubectl cp ./channel-artifacts/genesis.block %s" %(remote))

def create_dir_in_pod(domain):
  # wait for testpod to be up
  pod = ("kubectl exec %s-injector-pod --namespace=%s "
      "-- mkdir -p /var/hyperledger/orderer/ "
      "/var/hyperledger/production/orderer" %(domain, namespace)
    )
  res = os.system(pod)
  while(res != 0):
    puts("INFO: Waiting for pod to be up. Don't stop the process..")
    time.sleep(1)
    res = os.system(pod)

def generateTx():
  with open("channel-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      orderer_profile = config['orderer_profile']
      orderer_channel = config['orderer_channel']
      channel_profile = config['channel_profile']
      channel_id = config['channel_id']
      create_genesis = "./bin/configtxgen -profile " + orderer_profile + " -channelID " + orderer_channel + " -outputBlock ./channel-artifacts/genesis.block"
      create_channelTx = "./bin/configtxgen -profile " + channel_profile + " -outputCreateChannelTx ./channel-artifacts/" + channel_id + ".tx -channelID " + channel_id
      os.system(create_genesis)
      os.system(create_channelTx)
      total_organizations = config['total_organizations']
      for i in range(total_organizations):
        org_key = "org" + str(i+1) + "_msp"
        org_msp = config[org_key]
        create_OrgTx = "./bin/configtxgen -profile " + channel_profile + " -outputAnchorPeersUpdate ./channel-artifacts/" + org_msp +"anchors.tx -channelID " + channel_id + " -asOrg " + org_msp      
        os.system(create_OrgTx)
    
    except yaml.YAMLError as exc:
      puts(exc)
  return

def init():
  # generate crypto-config folder if not present
  if (not os.path.isdir('crypto-config')):
    puts("Generating crypto-config via cryptogen tool")
    os.system("./bin/cryptogen generate --config=./crypto-config.yaml")
  
  # generate channel-artifacts if not present
  if (not os.path.isdir('channel-artifacts')):
    puts("Generating channel-artifacts via configtxgen tool")
    os.system("export FABRIC_CFG_PATH=$PWD")
    os.system("mkdir channel-artifacts")
    generateTx()  
  
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      for orderer in config['OrdererOrgs']:
        name = orderer['Name'].lower()
        puts("%s : Creating Orderer Service.." %name)
        os.system("kubectl create namespace %s" %namespace)
        counter=0
        for spec in orderer['Specs']:
          domain = spec['CommonName']
          set_orderer_pvc(spec,orderer, domain)
          create_orderer_pod(domain)
          counter+=1

    except yaml.YAMLError as exc:
      puts(exc)
  return

init()
