#!/usr/bin/env python
"""
Check on Galera.
Report the seqno or server status.
"""


from __future__ import print_function
import sys

DEBUG = True


def debug_print(string):
    """Print a string to stdout when DEBUG is set to True."""
    if DEBUG:
        print("DEBUG: " + string)


def error_print(string):
    """Print a string to stderr."""
    print("ERROR: " + string, file=sys.stderr)


def status():
    """
    Return a word describing the status of mysqld or the initiator script.

    """
    # mock data
    print("stopped")


def seqno():
    """Return the log position of the database."""
    print(-1)


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
