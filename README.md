Galera Initiator
================

Python scripts to automatically bootstrap, join or recover a Galera cluster.

###Description
####Problem
When starting up a fresh Galera cluster, one node must be selected to be started with an cluster address: "gcomm://"
based on the status and log position of neighbouring nodes. Any subsequent nodes can be started normally, with the complete cluster address in their configuration file. Those nodes will then join the cluster.

When all nodes in a cluster are down (e.g. due to a catastrophic power outage), restarting them requires that you once again select one node and start it with an empty cluster address, essentially re-bootstrapping the cluster. Only then will other nodes be able to start up and join the cluster. Selection of that one bootstrapper node should happen by comparing the log positions on each node in the cluster. Only nodes with the furthest log position are eligible.

This process is relatively simple but cumbersome. Since it requires manual operator intervention, it's also not compatible with configuration management tools such as Puppet and Chef.

####Solution
The galera_check script can be used to determine the status and log position of an individual node. By exposing this script over a public interface such as an SNMP agent or CGI, the galera_init script can make an informed decision on wether or not to bootstrap a new cluster or to join an existing one.

The program logic of galera_init is laid out in the flowchart at the bottom of this document.


####Drawbacks
In certain failure scenarios, the galera_init will make decisions based on incomplete information.

Suppose a cluster of three nodes total, with two nodes up and one powered off. When both running cluster nodes are rebooted at the same time and the 3rd node is brought back up before the original two come back, galera_init will bootstrap a cluster on this third node while the log position is actually obsolete. When the nodes with a higher log position recover from their failure, they will join the running cluster and ***drop*** their data and request an SST.

This failure scenario something that extremely rarely if ever will occur in practice, but if it does, your data will be lost.

Please understand that Galera replication is not an acceptable substitute for frequent and well-tested backups.

###Installation
```pip install -U git+https://github.com/rasschaert/galera_initiator.git```

Dependencies:
- net-snmp python bindings
- psutil

###Usage
####galera_init
Start mysqld, either by joining an cluster existing cluster or by boostrapping a new one.

####galera_check
Requires either the 'seqno' or the 'status' parameter.

#####galera_check seqno
Calling galera_check with the seqno option returns the current log position on the local cluster node. This value is either retrieved from the grastate.dat file or recovered from a failed cluster by running mysqld with the ```--wsrep-recover``` option. If the seqno can't be found or recovered, the value returned will be the same of that of a fresh cluster node: -1.

#####galera_check status
Calling galera_check with the status option returns a one-word string status code that reflects the status of the local cluster node. Possible values in order of precedence:

Status        | Meaning
--------------|----------
bootstrapping | mysqld is starting, bootstrapping a new cluster
running       | mysqld is running, member of a cluster
initiating    | galera_init is running, will possibly soon bootstrap or join a cluster
stopped       | mysqld is stopped


###Vagrant
There's a [Vagrant environment](https://github.com/rasschaert/vagrant-galera) that installs a Galera cluster fully automatically using these scripts.

###To-do
- Make these things configurable:
  - The wsrep_cluster_address and wsrep_node_address can be found in /etc/my.cnf.d/galera.cnf
  - Net-SNMP runs on each cluster node and has extensions called galeraStatus and galeraSeqno
- Find alternative to submodule.check_output(), it was introduced in python 2.7 and CentOS 6 ships 2.6


###Flowchart
![galera-initiation-logic](http://i.imgur.com/RXTZLnH.png)
