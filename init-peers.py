#!/usr/bin/env python
import yaml
import os
import time
import sys
import subprocess
ordNamespace = sys.argv[1] if len(sys.argv) > 1 is not None else "peers"
def puts(str):
  print "\033[94m%s\033[0m" %str
  return
def exec_when_pod_up(cmd):
  res = os.system(cmd)
  while(res != 0):
    puts("INFO: Waiting for pod to be up. Don't stop the process..")
    time.sleep(1)
    res = os.system(cmd)
def set_peer_volume_claims(namespace, orgPeers, domain, orgName, ordNamespace):
  puts("%s : Creating Fabric Peer Persistent Volumes.." %namespace)
  for p in orgPeers:
    # create persistent volume claims
    res = create_peer_pvc(p, namespace, ordNamespace)
    if res != 0:
      continue
    # copy config content in created volume claim
    create_dir_in_pod(p, namespace, ordNamespace)
    copy_config(p, namespace, 'msp', domain, ordNamespace)
    copy_config(p, namespace, 'tls', domain, ordNamespace)
    # remove temporary pod
    os.system("kubectl delete pod %s-%s-injector-pod --namespace=%s" %(p['Hostname'], namespace, ordNamespace))
    # create actual fabric peer pod
    create_fabric_peer_pod(p, namespace, domain, orgPeers, orgName, ordNamespace)
  return
def create_fabric_peer_pod(peer, org, domain, orgPeers, orgName, ordNamespace):
  gossipPeer = [p for p in orgPeers if p['Hostname'] != peer['Hostname']][0]
  env = ("--set hlfpeer.orgname=%s --set hlfpeer.peername=%s --set hlfpeer.orgdomain=%s --set hlfpeer.gossipPeer=%s --set hlfpeer.peerOrgName=%s --set hlfpeer.port=%s --set hlfpeer.chaincodePort=%s --set hlfpeer.gossipPort=%s --set hlfpeer.portEvent=%s" %(org, peer['Hostname'], domain, gossipPeer['Hostname'], orgName, peer['Port'], peer['ChaincodePort'], peer['GossipPort'], peer['PortEvent']))
  puts(env)
  cmd = "helm install --name=%s ./org-peer --namespace=%s %s" %(peer['CommonName'],ordNamespace, env)
  puts(cmd)
  os.system(cmd)
def create_peer_pvc(peer, namespace, ordNamespace):
  cmd = ("helm install --name=pvc-%s ./org-peer-pvc --namespace=%s"
    " --set peername=%s --set orgname=%s" %(peer['CommonName'], ordNamespace, peer['Hostname'], namespace)
  )
  return os.system(cmd)
def create_dir_in_pod(peer, namespace, ordNamespace):
  cmd = ("kubectl exec %s-%s-injector-pod --namespace=%s "
    "-- mkdir -p /etc/hyperledger/fabric" %(peer['Hostname'], namespace, ordNamespace)
  )
  puts(cmd)
  exec_when_pod_up(cmd)
def copy_config(peer, namespace, subfolder, domain, ordNamespace):
  remotePath = "%s/%s-%s-injector-pod:/etc/hyperledger/fabric" %(ordNamespace, peer['Hostname'], namespace)
  src = "./crypto-config/peerOrganizations/%s/peers/%s/%s" %(domain, peer['CommonName'], subfolder)
  os.system("kubectl cp %s %s" %(src, remotePath))
  return
def set_org_cli(namespace, org, orderer, ordNamespace):
  domain = org['Domain']
  # create persistent volume claims for CLI
  res = os.system("helm install --name=cli-%s-pvc ./org-cli-pvc"
    " --set orgname=%s --set ordDomain=%s --set ordNamespace=%s "
    "--namespace=%s" %(namespace, namespace, orderer['Specs'][0]['CommonName'], ordNamespace, ordNamespace)
  )
  if res != 0:
    return
  cmd = ("kubectl exec %s-cli-injector-pod --namespace=%s "
    "-- mkdir -p /opt/gopath/src/github.com/hyperledger/fabric/orderer/crypto "
    "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations "
    "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations " %(namespace, ordNamespace)
  )
  # copy required files into the volume claim
  exec_when_pod_up(cmd)
  remoteBasePath = "/opt/gopath/src/github.com/hyperledger/fabric"
  pod = "%s/%s-cli-injector-pod" %(namespace, ordNamespace)
  puts("INFO: Copying channel-artifacts into CLI pvc")
  os.system("kubectl cp ./channel-artifacts %s:%s/peer" %(pod, remoteBasePath))
  puts("INFO: Copying chaincode into CLI pvc")  
  os.system("kubectl cp ./chaincode %s:/opt/gopath/src/github.com" %pod)
  puts("INFO: Copying peers certificates into CLI pvc")
  os.system(("kubectl cp ./crypto-config/peerOrganizations/%s "
    "%s:%s/peer/crypto/peerOrganizations" %(domain, pod, remoteBasePath)))
  puts("INFO: Copying orderer certificates into CLI pvc")  
  os.system("kubectl cp ./crypto-config/ordererOrganizations/%s/msp/tlscacerts "
    "%s:%s/peer/crypto/ordererOrganizations/%s" %(orderer['Domain'], pod, remoteBasePath, orderer['Domain']))
  os.system("kubectl cp ./crypto-config/ordererOrganizations/%s "
    "%s:%s/peer/crypto/ordererOrganizations" %(orderer['Domain'], pod, remoteBasePath))
  puts("INFO: Copyied configs into CLI pvc!! Removing test pod")
  # delete the temporary injector pod
  os.system("kubectl delete pod %s-cli-injector-pod --namespace=%s" %(namespace, ordNamespace))
  # Setting up actual CLI pod
  gossipVar = org['Specs'][1]['CommonName'] + ":" + str(org['Specs'][1]['Port'])
  os.system(("helm install --name=cli-%s ./org-cli --set orgName=%s --set orgDomain=%s --set corePeer=peer0 --set peerOrgName=%s --set port=%s --namespace=%s --set gossipPeer=%s" %(namespace, namespace, domain, org['Name'], org['Specs'][0]['Port'], ordNamespace, gossipVar)))
  return
##############################################
############ INITIALIZE METHOD ###############
##############################################
def init():
  # Generate crypto-config folder if not present via cryptogen tool
  if (not os.path.isdir('crypto-config')):
    os.system("./bin/cryptogen generate --config=./crypto-config.yaml")
    puts("Generating crypto-config via cryptogen tool")
  puts("Creating Namespace for all fabric components")
  os.system("kubectl create namespace %s" %ordNamespace)
  with open("crypto-config.yaml", 'r') as stream:
    try:
      config = yaml.load(stream)
      # Setting the Fabric Peer pods for each organization
      # as per specified in file crypto-config.yaml
      for org in config['PeerOrgs']:
        namespace = org['Name'].lower()
        set_peer_volume_claims(namespace, org['Specs'], org['Domain'], org['Name'], ordNamespace)
      for org in config['PeerOrgs']:
        namespace = org['Name'].lower()
        set_org_cli(namespace, org, config['OrdererOrgs'][0], ordNamespace)
    except yaml.YAMLError as exc:
      print(exc)
  return
init()
# Collapse




