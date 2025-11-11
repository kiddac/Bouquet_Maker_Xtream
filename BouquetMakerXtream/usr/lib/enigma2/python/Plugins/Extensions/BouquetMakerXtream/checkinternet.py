#!/usr/bin/python
# -*- coding: utf-8 -*-

debugs = False


def check_internet():
    if debugs:
        print("*** check_internent ***")
    try:
        with open('/proc/net/route', 'r') as f:
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 2:
                    interface, dest = fields[:2]
                    if dest == '00000000':  # Default route
                        return True
    except IOError:
        return True

    return False
