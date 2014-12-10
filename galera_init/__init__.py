#!/usr/bin/env python
"""
Galera initiator.

Setting up a Galera cluster usually requires one node to be manually started
first, with an empty wsrep_cluster_address. This is called boostrapping.
Only after starting that first server can the others join and form a cluster.

If no cluster is already active, an individual server will refuse to start
unless it has been instructed to bootstrap a new cluster.

After a complete cluster failure where all nodes are down, bootstrapping a
new cluster is required again. If not, individual servers will each refuse
to start. To select which server can bootstrap the new cluster after complete
failure, their seqno's must be compared. Only nodes with the highest seqno are
eligible to bootstap a cluster.

This script attempts to automate this process.

"""


from __future__ import print_function
import sys
import subprocess
import re
import time
import netsnmp

DEBUG = True
STATUS_TIMEOUT = 1000000
SEQNO_TIMEOUT = 6000000


def debug_print(string):
    """Print a string to stdout when DEBUG is set to True."""
    if DEBUG:
        print("DEBUG: " + string)


def error_print(string):
    """Print a string to stderr."""
    print("ERROR: " + string, file=sys.stderr)


def parse_config():
    """Parse the galera.cnf configuration file."""
    config_file_path = "/etc/my.cnf.d/galera.cnf"
    try:
        config_file = open(config_file_path, "r")
    except IOError:
        error_print("Could not open %s. Make sure it exists." %
                    config_file_path)
        exit_boostrapper(False)
    for line in config_file:
        # Find the line with the cluster address
        cluster_address_match = \
            re.search(r"wsrep_cluster_address\s*=\s*gcomm://(.*)", line)
        if cluster_address_match:
            # The first group is a list of comma-separated hosts
            # Remove the spaces, if any, and split on the comma
            nodes = cluster_address_match.group(1).replace(" ", "").split(",")
        node_address_match = re.search(r"wsrep_node_address\s*=\s*(.*)", line)
        if node_address_match:
            # The first group is the local host
            # Remove the spaces, if any
            local_node = node_address_match.group(1).replace(" ", "")
    config_file.close()
    return (local_node, nodes)


def string_to_oid(name):
    """
    Convert an net-snmp string index to an OID.

    The OID starts with nsExtendOutput1Line, followed by the length of the
    string index, followed by the ASCII values for the individual characters.
    Returns a fully qualified, dotted-decimal, numeric OID.

    """
    oid_prefix = ".1.3.6.1.4.1.8072.1.3.2.3.1.1"
    ascii_values = [str(ord(element)) for element in list(name)]
    return ".".join([oid_prefix, str(len(name))] + ascii_values)


def snmp(oid, host, timeout=1000000):
    """Perform an SNMP lookup of an OID on a host, return the result."""
    debug_print("Quering SNMP agent on %s for OID '%s'." % (host, oid))
    var = netsnmp.Varbind(oid)
    result = netsnmp.snmpget(var, Version=2, DestHost=host, Community="public",
                             Timeout=timeout, Retries=0)
    debug_print("SNMP lookup returned result '%s'." % (result[0]))
    return result[0]


def get_status(host):
    """Look up the status of a certain host and return a string."""
    debug_print("Looking up Galera status of node %s." % (host))
    snmp_result = snmp(string_to_oid("galeraStatus"), host. STATUS_TIMEOUT)
    if snmp_result is not "None":
        return snmp_result
    else:
        return "unreachable"


def get_seqno(host):
    """Return the seqno of a certain host."""
    debug_print("Looking up database seqno of node %s." % (host))
    snmp_result = snmp(string_to_oid("galeraSeqno"), host, SEQNO_TIMEOUT)
    if snmp_result is not "None":
        return snmp_result
    else:
        return -1


def join_cluster():
    """Join an existing cluster."""
    # stub
    print("Joining cluster (by running '/etc/init.d/mysql start').")
    exit_code = subprocess.call(["/etc/init.d/mysql", "start"])
    debug_print("exit code is %s" % exit_code)
    if not exit_code:
        error_print("Joining cluster!")
    return exit_code


def bootstrap_cluster():
    """Bootstrap a new cluster."""
    print("Bootstrapping cluster (by running '/etc/init.d/mysql bootstrap').")
    exit_code = subprocess.call(["/etc/init.d/mysql", "bootstrap"])
    debug_print("exit code is %s" % exit_code)
    if exit_code:
        error_print("Bootstrapping failed!")
    return exit_code


def exit_boostrapper(code=0):
    """Exit this script."""
    print("Exiting bootstrapper.")
    sys.exit(code)


def main():
    """The main function."""
    local_node, nodes = parse_config()
    local_status = get_status(local_node)
    if not local_status == "initiating":
        if local_status == "stopped":
            error_print("Something is wrong with the galera-check script.")
            exit_boostrapper(1)
        print("Local node is already active. Nothing to do.")
        exit_boostrapper()
    debug_print("Going to sleep for a while to prevent race conditions.")
    # Sleep the time it takes to get the seqno + the time it takes to get
    # the status for each node in the list
    time.sleep((STATUS_TIMEOUT + SEQNO_TIMEOUT) * len(nodes))
    eligible = True
    local_seqno = get_seqno(local_node)
    local_prio = float("inf")
    for node_prio, node in enumerate(nodes):
        debug_print("Processing node %s, has prio %s." %
                    (node, node_prio))
        if local_node == node:
            local_prio = node_prio
            debug_print("IP address %s is on this machine." % (node))
            debug_print("Local priority is %s." % (local_prio))
        else:
            node_status = get_status(node)
            debug_print("Status on node %s is %s." %
                        (node, node_status))
            if node_status == "started" or node_status == "starting":
                exit_boostrapper(join_cluster())
            elif node_status == "bootstrapping":
                print("Waiting for %s to finish bootstrapping." % (node))
                time.sleep(10)
                exit_boostrapper(join_cluster())
            elif node_status == "unreachable":
                # If a node is unreachable, we can't ask for its seqno
                pass
            elif node_status == "stopped" or node_status == "initiating":
                node_seqno = get_seqno(node)
                debug_print("seqno for %s is %s." % (node, node_seqno))
                if node_seqno > local_seqno:
                    debug_print("Seqno of %s is %s Local seqno is %s" %
                                (node, node_seqno, local_seqno))
                    print("Seqno of local node has been outbid. Local node " +
                          "is no longer eligible for bootstrapping.")
                    eligible = False
                    break
                elif local_prio > node_prio and node_status == "initiating":
                    debug_print("Prio of %s is %s, local prio is %s." %
                                (node, str(node_prio), str(local_prio)))
                    print(
                        "Seqno of local node has been outbid. " +
                        "Local node is no longer eligible for bootstrapping."
                        )
                    eligible = False
                    break
    debug_print("Exited node processing loop.")
    if eligible:
        exit_boostrapper(bootstrap_cluster())
    else:
        exit_boostrapper()


if __name__ == '__main__':
    main()
