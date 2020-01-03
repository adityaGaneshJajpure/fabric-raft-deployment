# Implementation of Multi-ordering Raft Service for Hyperledger Fabric on Kubernetes with Helm

Raft consensus provide a shared load for ordering service, to increase fault-tolerence. After reading this blog, What you have:
1. A running multi-orderer service with five orderers.
2. A running fabric network with RAFT implemented.

## Pre-Requisites

Have installed 
git https://www.linode.com/docs/development/version-control/how-to-install-git-on-linux-mac-and-windows/, 
python2 https://docs.python-guide.org/starting/install/linux/,
helm https://helm.sh/docs/intro/install/,
kubectl https://kubernetes.io/docs/tasks/tools/install-kubectl/,
context of kubectl might be set at any of minikube or your other kubernetes cluster.

## Steps for basic set-up

1. Clone the Repository `git clone https://github.com/adityaJajpure/fabric-raft-deployment.git`
2. Edit crypto-config.yaml, configtx.yaml, & channel-config.yaml as per your requirement.
3. run command `make orderer-up` or `python init-orderer-up.py <namespace>`
4. run command to set current-namespace `kubectl config set-context --current --namespace=peers` (peers because we used peers as a namespace here)
5. check if all orderer status are set to running `kubectl get po`, wait till all are running
6. run command `make peer-up` or `python init-peers-up.py <namespace>`
7. check if all peers status are set to running `kubectl get po`, wait till all are running
8. check logs of any of the orderer using `kubectl logs -f <name-of-orderer-pod>`, you can see the current election status, leader status etc. This signs your sucessful raft working.

## What you have done so far

Let us dive into the code, what we have done.

### crypto-config.yaml

This file is the source of physical configuration you want to create for your fabric network. 

This snippet shows the orderers configuration you created.

Name : It is the name of your orderer organization
Domain : It is the domain name of your orderer organization
Specs : Here, you are reqired to mention Hostname & CommonName for your orderers. Mention configuration on the basis of number of orderers you required.

This snippet shows the peers configuration you created.

Name : It is the name of your peer organization
Domain : It is the domain name of your peer organization
Specs : Here you can add as many peers you want for your organization. It contains field for HostName, CommonName, Port, EventPort, ChaincodePort, GossipPort. `You required to change only Name & Domain`.

The snippet above is for organization with 3 peers. Add or remove number of peers by updating Specs key.

### configtx.yaml

This file is the source of logical configuration you want to create for your fabric network. 

### what to Update in configtx.yaml(atleast)

-> Name & MSPID of orderer & organizations (replace Org1 & Org2 with your organiztions name *Edit uppercase & lowercase properly*)

-> Replace example with your domain (same domain you mentioned in orderer configuration in crypto-config.yaml)

-> update domain name properly for orderer organization in profile section.

### channel-config.yaml

All the data in this file must be filled up carefully. The script internally is dependent on this file.
orderer_profile consist of the same value as the profile section orderer of configtx.yaml file.
orderer_channel is the default channel for orderer.
channel_profile is the name of channel, which also required to be the same as channel name in profile section of configtx.yaml.
total_organizations is the number of organizations other than orderer.
msp id is with a format org<number(1-to-n)>_msp, contains msp id of organizations. This also is the same as MSP ID mentioned for each organization in configtx.yaml file. n is number of organizations.

### python script

If you not aware with python, still no worry. You can create a bash script too simply by using all the commands this script ran using `os.system()` directly.

What this script gonna do:

1. Create crypto-config & channel-artifact folder having all the org certificates (including orderer) & genesis block using cryptogen & configtxgen tool respectively.
2. Create volumes for orderer and copy the required certificates in them.
3. Create volumes for peers and copy the required certificates in them.
4. Release pods which are no more required (ie. temporary pod we created to copy the data).

*Note : Do not interrupt the script due to any reason. Let it be finish by itself*

### orderer & orderer-pvc

Helm release with Deployment, persistent volume claim & service for orderer.
With the help of python script init-orderer-raft.py, we spin up the orderer pods. In that script, we use these helm charts.
The orderer-pvc helm chart here is used to spin up persistent volume claims and a temporary pod. Python script init-orderer-raft.py install this helm release, copy the crypto-certs & all required stuff to the orderer persistent volume with the help of temporary pod, & then delete that temporary pod.
The orderer helm chart here is used to spin up the orderer deployment and orderer service. Again, python script init-orderer-raft.py install this helm release. 
We also mount the same volume to which we copied data using that temporary pod with our orderer pod. In this way, we get all the required fabric crypto-material in our orderer pods.

### org-peer & org-peer-pvc

Helm release with Deployment, persistent volume claim & service for the organization other than orderer. With the help of python script init-peer.py, we spin up the org-peer pods. In that script, we use these helm charts.
The org-peer-pvc helm chart here is used to spin up persistent volume claims and a temporary pod. Python script init-peer.py install this helm release, copy the crypto-certs & all required stuff to the org-peer persistent volume with the help of temporary pod, & then delete that temporary pod.
The org-peer helm chart here is used to spin up the org-peer deployment and org-peer service. Again, python script init-peer.py install this helm release. 
We also mount the same volume to which we copied data using that temporary pod with our peer pod. In this way, we get all the required fabric crypto-material in our orderer pods.

### org-cli & org-cli-pvc

Helm release with Deployment, persistent volume claim & service for the org-cli. With the help of python script init-peer.py, we spin up the cli pods. In that script, we use these helm charts.
The org-cli-pvc helm chart here is used to spin up persistent volume claims and a temporary pod. Python script init-peer.py install this helm release, copy the crypto-certs & all required stuff to the org-cli persistent volume with the help of temporary pod, & then delete that temporary pod.
The org-cli helm chart here is used to spin up the org-cli deployment and peer service. Again, python script init-peer.py install this helm release. 
We also mount the same volume to which we copied data using that temporary pod with our peer pod. In this way, we get all the required fabric crypto-material in our orderer pods.
