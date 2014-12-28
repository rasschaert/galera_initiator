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
import time
import netsnmp
import ConfigParser
import os

DEBUG = True
STATUS_TIMEOUT = 1
SEQNO_TIMEOUT = 6


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
    config = ConfigParser.RawConfigParser()
    config.read(config_file_path)
    try:
        # Look up the cluster_address.
        cluster_address = config.get("galera", "wsrep_cluster_address")
    # If the file doesn't contain that setting, quit.
    except ConfigParser.NoOptionError:
        error_print("Couldn't find wsrep_cluster_address setting in %s" %
                    (config_file_path))
        exit_script(1)
    nodes = cluster_address.replace("gcomm://", "").split(",")
    try:
        # Look up the node_address.
        local_node = config.get("galera", "wsrep_node_address")
    # If the file doesn't contain that setting, quit.
    except ConfigParser.NoOptionError:
        error_print("Couldn't find wsrep_node_address setting in %s" %
                    (config_file_path))
        exit_script(1)
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


def snmp(oid, host, timeout=1):
    """Perform an SNMP lookup of an OID on a host, return the result."""
    debug_print("Quering SNMP agent on %s for OID '%s'." % (host, oid))
    var = netsnmp.Varbind(oid)
    result = netsnmp.snmpget(var, Version=2, DestHost=host, Community="public",
                             Timeout=(timeout * 1000000), Retries=0)
    debug_print("SNMP lookup returned result '%s'." % (result[0]))
    return result[0]


def get_status(host):
    """Look up the status of a certain host and return a string."""
    debug_print("Looking up Galera status of node %s." % (host))
    snmp_result = snmp(string_to_oid("galeraStatus"), host, STATUS_TIMEOUT)
    if snmp_result is not None and snmp_result != "":
        return snmp_result
    else:
        return "unreachable"


def get_seqno(host=None):
    """Return the seqno of a certain host."""
    if host is None:
        proc = subprocess.Popen(["/usr/bin/galera_seqno"],
                                stdout=subprocess.PIPE)
        return proc.communicate()[0]
    debug_print("Looking up database seqno of node %s." % (host))
    snmp_result = snmp(string_to_oid("galeraSeqno"), host, SEQNO_TIMEOUT)
    if snmp_result is not None:
        return snmp_result
    else:
        return -1


def mysqld_status_check(attempts):
    """Attempt a number of times to ping mysqld, return result."""
    debug_print("Checking status of mysqld.")
    for iteration in range(attempts):
        debug_print("Health check attempt number %d." % (iteration+1))
        devnull = open(os.devnull, 'w')
        returncode = subprocess.call(["/usr/bin/mysqladmin", "ping"],
                                     stdout=devnull, stderr=subprocess.STDOUT)
        devnull.close()
        debug_print("Health check return code is %s" % returncode)
        if returncode == 0:
            return 0
        if (iteration + 1) < attempts:
            time.sleep(1)
    return returncode


def join_cluster():
    """Join an existing cluster."""
    # stub
    debug_print("Joining cluster ('/etc/init.d/mysql start').")
    proc = subprocess.Popen(["/etc/init.d/mysql", "start"],
                            stdout=subprocess.PIPE)
    debug_print(proc.communicate()[0])
    debug_print("return code is %s" % proc.returncode)
    if proc.returncode != 0:
        error_print("Joining cluster failed!")
        return proc.returncode
    return mysqld_status_check(10)


def bootstrap_cluster():
    """Bootstrap a new cluster."""
    debug_print("Bootstrapping cluster ('/etc/init.d/mysql bootstrap').")
    proc = subprocess.Popen(["/etc/init.d/mysql", "bootstrap"],
                            stdout=subprocess.PIPE)
    debug_print(proc.communicate()[0])
    debug_print("return code is %s" % proc.returncode)
    if proc.returncode != 0:
        error_print("Bootstrapping failed!")
        return proc.returncode
    return mysqld_status_check(10)


def exit_script(code=0):
    """Exit this script."""
    debug_print("Exiting script.")
    sys.exit(code)


def set_lock():
    """Create a lock file in /var/lock/."""
    debug_print("Creating lock file.")
    open('/var/lock/galera_init', 'a').close()


def clear_lock():
    """Remove the lock file created by set_lock()."""
    debug_print("Clearing lock file.")
    try:
        os.remove('/var/lock/galera_init')
    except OSError:
        pass


def determine_eligibility(available_nodes):
    """
    Compare seqno of local node to that of available other nodes to
    determine eligibility to bootstrap a new cluster. Return a boolean.
    """
    eligible = True
    if not available_nodes:
        return eligible
    local_seqno = get_seqno()
    debug_print("Local seqno is %s." % (local_seqno))
    for node in available_nodes:
        node_seqno = get_seqno(node)
        debug_print("Seqno of %s is %s." % (node, node_seqno))
        if node_seqno > local_seqno:
            debug_print("Seqno of local node has been outbid. Local node " +
                  "is no longer eligible for bootstrapping.")
            eligible = False
            break
    return eligible


def main():
    """The main function."""
    local_node, nodes = parse_config()
    time.sleep(5)
    local_status = get_status(local_node)
    if not local_status == "initiating":
        if local_status == "stopped":
            error_print("Something is wrong with the galera_status script.")
            exit_script(1)
        debug_print("Local node is already active. Nothing to do.")
        exit_script()
    debug_print("Going to sleep for a while to prevent race conditions.")
    # Sleep the time it takes to get the status for each node in the list
    time.sleep(STATUS_TIMEOUT * len(nodes))
    available_nodes = []
    local_prio = float("inf")
    for node_prio, node in enumerate(nodes):
        debug_print("Processing node %s, has prio %s." %
                    (node, node_prio))
        if local_node == node:
            local_prio = node_prio
            debug_print("IP address %s is on this machine." % (node))
            debug_print("Local priority is %s." % (local_prio))
        else:
            repeat = True
            while repeat:
                node_status = get_status(node)
                debug_print("Status on node %s is %s." %
                            (node, node_status))
                if node_status == "locked":
                    time.sleep(2)
                elif node_status == "initiating":
                    if node_prio < local_prio:
                        time.sleep(2)
                    else:
                        available_nodes.append(node)
                        repeat = False
                elif node_status == "stopped":
                    available_nodes.append(node)
                    repeat = False
                elif node_status == "running":
                    exit_script(join_cluster())
                    repeat = False
                elif node_status == "bootstrapping":
                    debug_print("Waiting for %s to finish bootstrapping." %
                                (node))
                    time.sleep(5)
                    exit_script(join_cluster())
                elif node_status == "unreachable":
                    repeat = False
    set_lock()
    eligible = determine_eligibility(available_nodes)
    success = 0
    if eligible:
        success = bootstrap_cluster()
    clear_lock()
    exit_script(success)


if __name__ == '__main__':
    main()
