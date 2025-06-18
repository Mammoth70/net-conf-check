#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Analysis of the structure of the network equipment configuration file.
Checking the declaration of used objects.
Checking the use of declared objects.

'''
import sys
sys.path.append('..')
import re
import argparse
import yaml
import logging

r_name = 'Shiva'
r_fullname = '\n' + r_name + ' - automation system for administration of telecommunication equipment\n'
r_version = 'ver. 1.3.7  - 17.06.2025'
r_copyright = 'Author: Andrey Yakovlev (andrey-yakovlev@yandex.ru) ' + r_version
r_params = 'command line options'
r_help = 'help'
r_help1 = 'help output'


#DB =  {
#'interface' : {                                 # name of the property
#    'declared' : [                              # list of regexps to search for declared objects
#        r'^interface (?P<name>\S+)$'
#        ]
#    'declared_added' : ['default']              # list of objects to be added to declared ones
#    'used' : [                                  # list of regexps to search for used objects
#        r'[ -]interface (?P<name>\S+)$'
#        ], 
#    'check_unused' : False,                     # flag for checking declared but not used objects
#    'used_added' : []                           # list of objects to be added to used
#}


# # Global variables
lines = []      # list of lines in the configuration file, leading and trailing spaces must be preserved
tree = {}       # dictionary of sections of the configuration file, where key is the line number, and value is the line number of the beginning of the section
location = {}   # dictionary, where key is an object and value is the line number where it occurs


def exists_file(file_name):
    '''
    Checks a file exists.
    '''
    return os.path.isfile(file_name)


def load_from_file(input_file):
    '''
    Loads a structure from a yaml file and returns it.
    '''
    if not exists_file(input_file):
        logging.error('File ' + input_file + ' not found')
        return None
    with open(input_file, 'r') as f:
        result = yaml.safe_load(f)
    return result


def setup_logging():
    '''
    Configures logging formats and levels.
    '''
    logging.basicConfig(
        format = 'Shiva says --  %(levelname)s:  %(message)s',
        level=logging.INFO)
    logging.getLogger('paramiko').setLevel(logging.WARNING)


def print_full_name():
    '''
    Displays the system name.
    '''
    print(r_fullname, file=sys.stderr)


def load_conf_from_text(input_file):
    '''
    Loads the configuration from a file into the list.
    Makes a dictionary of tree sections, where key is the line number, and value is the line number of the beginning of the section.
    '''
    global lines
    global tree

    with open(input_file, 'r') as f:
        lines = [line.strip(('\n\r')) for line in f]

    parent = 0
    for num, line in enumerate(lines):
        if not line.startswith(' '):
            parent = num
        tree[num] = parent

    return None


def load_obj(regex, debug=False):
    '''
    Fills the set of declared any objects from the list.
    Makes a location dictionary, where key is the object and value is the line number where it occurred.
    '''
    global lines
    global location
    objs = set()
    for num, line in enumerate(lines):
        match = re.search(regex, line)
        if match:
            obj = match.group('name')
            if debug:
                print(obj)
            objs.add(obj)
            location[obj] = num
    return objs


def print_check_objs_err(num, name, objname):
    '''
    Displays the error of an undeclared object and the text in which it occurs.
    '''
    global lines
    global tree
    if tree[num] == num:
        print('\n{0}\n   >>> not declared, but used {2} \"{3}\" (line {1}) <<<'.format(lines[num], num+1, objname, name))
    elif tree[num] == (num-1):
        print('\n{0}\n{1}\n   >>> not declared, but used {3} \"{4}\" (line {2}) <<<'.format(lines[tree[num]], lines[num], num+1, objname, name))
    else:
        print('\n{0}\n ...\n{1}\n   >>> not declared, but used {3} \"{4}\" (line {2}) <<<'.format(lines[tree[num]], lines[num], num+1, objname, name))
    return None


def print_check_objs_used_err(s, objname):
    '''
    Returns a declared but unused object error.
    '''
    global lines
    global location
    for obj in s:
        if location.get(obj):
            print('\n{0}\n   >>> declared but not used {2} \"{3}\" (line {1}) <<<'.format(lines[location[obj]], location[obj]+1, objname, obj))
        else:
            print('\n{0}\n   >>> declared but not used {1} \"{2}\" <<<'.format('default declared', objname, obj))
    return None


def check_objs(regex, objs, objname, debug=False):
    '''
    Checks liness with any objects for the presence of an object.
    '''
    global lines
    objs_used = set()
    for num, line in enumerate(lines):
        match = re.search(regex, line)
        if match:
            obj = match.group('name')
            if debug:
                print(obj)
            objs_used.add(obj)
            if obj not in objs:
                print_check_objs_err(num, obj, objname)
    return objs_used


def check_objs_used(objs, objs_used, objname):
    '''
    Checks for the presence of declared but not used objects.
    '''
    s = objs - objs_used
    if (len(s) > 0):
        print_check_objs_used_err(s, objname)
    return None


def conf_run(args):
    if exists_file(args.source):
        print('Checking configuration from file {}'.format(args.source))
        load_conf_from_text(args.source)

        DB = load_from_file(args.database)

        for key in DB.keys():
            # Loading object descriptions
            objects = set()
            for regex in DB[key].get('declared', []):
                objects = objects | load_obj(regex, DB[key].get('debug_load', False))
            for added in DB[key].get('declared_added', []):
                objects.add(added)

            # Checking the declaration of used objects
            objects_used = set()
            for regex in DB[key].get('used', []):
                objects_used = objects_used | check_objs(regex, objects, key, DB[key].get('debug_check', False))
            for added in DB[key].get('used_added', []):
                objects_used.add(added)

            # Checking the use of declared objects
            if DB[key].get('check_unused', True):
                check_objs_used(objects, objects_used, key)
    else:
        print('\nFile {} not found'.format(args.source))

    return None


def create_parser():
    '''
    Command line parser.
    '''
    desprg = 'The script analyzes the correctness of the declaration and use of objects in the configuration file.'
    parser = argparse.ArgumentParser(prog = 'net-conf-check',
                                        description = desprg,
                                        add_help = False,
                                        epilog = r_copyright )
    pr_group = parser.add_argument_group (title=r_params)
    pr_group.add_argument('-h', action=r_help, help=r_help1)
    pr_group.add_argument('-d',
                          dest='database',
                          default='net-conf-check-cisco.yml',
                          help='configuration object dictonary')
    pr_group.add_argument('-s',
                          dest='source',
                          required=True,
                          help='configuration file')
    pr_group.set_defaults(func=conf_run)
    return parser


if __name__ == '__main__':
    setup_logging()
    print_full_name()
    parser = create_parser()
    args = parser.parse_args()
    if not vars(args):
        parser.print_usage()
    else:
        args.func(args)
