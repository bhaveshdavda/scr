#! /usr/bin/env python3

import os, sys

if 'scrjob' not in sys.path:
    sys.path.insert(0, '/'.join(os.path.realpath(__file__).split('/')[:-2]))
    import scrjob

import argparse

from scrjob.prerun import prerun
from scrjob.scr_environment import SCR_Env
from scrjob.resmgrs import AutoResourceManager

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p',
                        '--prefix',
                        metavar='<dir>',
                        type=str,
                        default=None,
                        help='Specify the prefix directory.')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        default=False,
                        help='Verbose output.')

    args = parser.parse_args()

    scr_env = SCR_Env(prefix=args.prefix)
    scr_env.resmgr = AutoResourceManager()

    prerun(scr_env=scr_env, verbose=args.verbose)
