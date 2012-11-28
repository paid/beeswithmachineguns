#!/bin/env python

"""
The MIT License

Copyright (c) 2010 The Chicago Tribune & Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import bees
import re
from argparse import ArgumentParser, Action

NO_TRAILING_SLASH_REGEX = re.compile(r'^.*?\.\w+$')


def parse_arguments():
    """
    Handle the command line arguments for spinning up bees
    """
    parser = ArgumentParser(
        description="Bees with Machine Guns: A utility for arming "
        "(creating) many bees (small EC2 instances) to attack (load "
        "test) targets (web applications).")

    subparsers = parser.add_subparsers(dest='subparser_name',
        help='Bee commands')

    up_subparser = subparsers.add_parser(
        "up",
        help="In order to spin up new servers you will need to specify "
        "at least the -k command, which is the name of the EC2 keypair "
        "to use for creating and connecting to the new servers. "
        "The bees will expect to find a .pem file with this name in ~/.ssh/."
    )

    up_subparser.add_argument(
        '-k', '--key', metavar="KEY",
        action='store', dest='key', type=str,
        help="The ssh key pair name to use to connect to the new servers.")
    up_subparser.add_argument(
        '-s', '--servers', metavar="SERVERS",
        action='store', dest='servers', type=int, default=5,
        help="The number of servers to start (default: 5).")
    up_subparser.add_argument(
        '-g', '--group', metavar="GROUP",
        action='store', dest='group', type=str, default='default',
        help="The security group to run the instances under "
        "(default: default).")
    up_subparser.add_argument(
        '-z', '--zone',  metavar="ZONE",
        action='store', dest='zone', type=str, default='us-east-1d',
        help="The availability zone to start the instances "
        "in (default: us-east-1d).")
    up_subparser.add_argument(
        '-i', '--instance',  metavar="INSTANCE",
        action='store', dest='instance', type=str, default='ami-ff17fb96',
        help="The instance-id to use for each server from "
        "(default: ami-ff17fb96).")
    up_subparser.add_argument(
        '-l', '--login',  metavar="LOGIN",
        action='store', dest='login', type=str, default='newsapps',
        help="The ssh username name to use to connect to the "
        "new servers (default: newsapps).")

    attack_subparser = subparsers.add_parser(
        "attack",
        help="Beginning an attack requires only that you specify the "
        "-u option with the URL you wish to target.")

    attack_subparser.add_argument(
        '-u', '--url', metavar="URL",
        action='store', dest='url', type=str,
        help="URL of the target to attack.")
    attack_subparser.add_argument(
        '-n', '--number', metavar="NUMBER",
        action='store', dest='number', type=int, default=1000,
        help="The number of total connections to make to "
        "the target (default: 1000).")
    attack_subparser.add_argument(
        '-c', '--concurrent', metavar="CONCURRENT",
        action='store', dest='concurrent', type=int, default=100,
        help="The number of concurrent connections to make "
        "to the target (default: 100).")
    attack_subparser.add_argument(
        '-H', '--headers', metavar='HEADERS', nargs='*',
        action=HeadersAction, dest='headers', type=str,
        help="Send arbitray header line(s) along with the attack, "
        "eg. 'Host: www.chicagotribune.com'; Inserted after all normal "
        "header lines. (repeatable)",
        default=''
    )
    attack_subparser.add_argument(
        '-C', '--cookies', metavar='COOKIES', nargs='*',
        action=CookiesAction, dest='cookies', type=str,
        help="Add cookie, eg. 'Apache=1234'. (repeatable)",
        default=''
    )

    exec_subparser = subparsers.add_parser(
        "exec",
        help="Execute an arbitrary command")
    exec_subparser.add_argument(
        '-o', '--outfile', metavar="OUTFILE",
        action='store', dest='outfile', type=str,
        help="The local file to write the bees' responses")
    exec_subparser.add_argument(
        '-', action=RemoteCommandAction, dest='remote_command',
        nargs='*', required=True,
        help="The command each bee should execute")

    down_subparser = subparsers.add_parser(
        "down",
        help="Call off the swarm")

    report_subparser = subparsers.add_parser(
        "report",
        help="Print the active bees' status")


    options = parser.parse_args()

    if options.subparser_name == 'up':
        if not options.key:
            parser.error(
                "To spin up new instances you need to specify a "
                "key-pair name with -k")

        if options.group == 'default':
            print "New bees will use the \"default\" EC2 security group. "
            "Please note that port 22 (SSH) is not normally open on this "
            "group. You will need to use to the EC2 tools to open it "
            "before you will be able to attack."

        bees.up(
            options.servers, options.group, options.zone,
            options.instance, options.login, options.key)
    elif options.subparser_name == 'attack':
        if not options.url:
            parser.error('To run an attack you need to specify a url with -u')

        if NO_TRAILING_SLASH_REGEX.match(options.url):
            parser.error(
                "It appears your URL lacks a trailing slash, this "
                "will disorient the bees. Please try again with a "
                "trailing slash.")

        bees.attack(
            options.url, options.number, options.concurrent,
            options.headers, options.cookies)
    elif options.subparser_name == 'exec':
        bees.execute(
            options.remote_command,
            lambda x: bees.write_results(x, options.outfile))
    elif options.subparser_name == 'down':
        bees.down()
    elif options.subparser_name == 'report':
        bees.report()


class HeadersAction(Action):
    """
    Join 'headers' arguments, creating an argument string that
    can be used when calling ab in the attack
    """
    def __call__(self, parser, namespace, values, option_string=None):
        headers = ' '.join([
            '-H "%s"' % header for header in values
        ])
        setattr(namespace, self.dest, headers)


class CookiesAction(Action):
    """
    Join 'cookies' arguments, creating an argument string that
    can be used when calling ab in the attack
    """
    def __call__(self, parser, namespace, values, option_string=None):
        cookies = ' '.join([
            '-C "%s"' % cookie for cookie in values
        ])
        setattr(namespace, self.dest, cookies)


class RemoteCommandAction(Action):
    """
    Join the parts of the remote command into a single string suitable for
    executing from the command-line
    """
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, ' '.join(values))


def main():
    parse_arguments()
