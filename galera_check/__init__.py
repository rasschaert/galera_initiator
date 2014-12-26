#!/usr/bin/env python
"""
Check on Galera.
Report the seqno or server status.
"""


from __future__ import print_function
import sys
import psutil
import ConfigParser
import io
import subprocess
import re
import os.path

DEBUG = True


def debug_print(string):
    """Print a string to stdout when DEBUG is set to True."""
    if DEBUG:
        print("DEBUG: " + string)


def error_print(string):
    """Print a string to stderr."""
    print("ERROR: " + string, file=sys.stderr)


def safe_process(pid, attr):
    """
    Get process attributes safely, return attribute of psutil.Process object.
    """
    try:
        return getattr(psutil.Process(pid), attr)
    except psutil.error.NoSuchProcess:
        return ""


def is_boostrap_process_running(pid_list=psutil.get_pid_list()):
    """
    Check whether the mysql init script is running with the
    --wsrep-new-cluster option. Return a boolean.
    """
    return ['/bin/sh', '/etc/init.d/mysql', 'start',
            '--wsrep-new-cluster'] in [safe_process(pid, "cmdline") for
                                       pid in pid_list]


def is_recover_process_running(pid_list=psutil.get_pid_list()):
    """
    Check whether the mysqld process is running with the --wsrep-recover
    option. Return a boolean.
    """
    return ['/bin/sh', '/usr/bin/mysqld_safe', '--wsrep-recover'] in \
           [safe_process(pid, "cmdline") for pid in pid_list]


def is_mysqld_process_running(pid_list=psutil.get_pid_list()):
    """Check whether the mysqld process is running. Return a boolean."""
    return "mysqld" in [safe_process(pid, "name") for pid in pid_list]


def is_galera_init_process_running(pid_list=psutil.get_pid_list()):
    """Check whether the galera_init process is running. Return a boolean."""
    return "galera_init" in [safe_process(pid, "name") for pid in pid_list]


def lock_file_exists():
    """
    Check if a lock file exists at /var/lock/galera_init.
    Return a boolean.
    """
    return os.path.isfile('/var/lock/galera_init')


def status():
    """
    Print a word describing the status of mysqld or the initiator script.
    """
    # Get a list of all currently running processes.
    pid_list = psutil.get_pid_list()
    # Check if a process looks like a bootstrap process.
    if is_boostrap_process_running(pid_list):
        print("bootstrapping")
    # Check if a process looks like a recover process.
    elif is_recover_process_running():
        # It doesn't really mean that the local machine is locked,
        # but that another node probably has the lock.
        print("locked")
    # Check if a process looks like a galera_init process.
    elif is_mysqld_process_running(pid_list):
        print("running")
    # Check if a lock file exists
    elif lock_file_exists():
        print("locked")
    # Check if a process looks like a galera_init process.
    elif is_galera_init_process_running(pid_list):
        print("initiating")
    # If none of the above is true, the status is simply stopped.
    else:
        print("stopped")
    sys.exit(0)


def seqno():
    """Print the log position of the database."""
    grastate_file_path = "/var/lib/mysql/grastate.dat"
    try:
        grastate_file = open(grastate_file_path)
    except IOError:
        recover_seqno()
    # The grastate.dat file is technically not valid ini, because it doesn't
    # have a header. Prepend a header so ConfigParser doesn't notice.
    # http://stackoverflow.com/questions/2819696/
    grastate_ini = u'[grastate]\n'+''.join([x for x in grastate_file])
    config = ConfigParser.RawConfigParser()
    config.readfp(io.StringIO(grastate_ini))
    try:
        # Look up and print the seqno.
        print(config.get("grastate", "seqno"))
    # If the grastate.dat file exists but doesn't contain a seqno, use default.
    except ConfigParser.NoOptionError:
        recover_seqno()


def recover_seqno():
    """Print -1 when the real seqno can't be determined."""
    if not is_mysqld_process_running():
        proc = subprocess.Popen(['/usr/bin/mysqld_safe', '--wsrep-recover'],
                                stdout=subprocess.PIPE)
        output = proc.communicate()[0]
        for line in output.split('\n'):
            recovered_match = re.search(r"WSREP: Recovered position(.*)", line)
            if recovered_match:
                print(recovered_match.group(1).split(":")[1])
        sys.exit(0)
    print(-1)
    sys.exit(0)


def main(argv):
    """The main function."""
    if len(argv) > 1:
        if argv[1] == 'status':
            status()
            sys.exit(0)
        if argv[1] == 'seqno':
            seqno()
            sys.exit(0)
    error_print("Please run this command with either the 'status' or "
                + "'seqno' argument.")
    sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)
