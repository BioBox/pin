
"""pin.py -- Entry point for pin."""

import argparse
import curses
import typing

# import pin.infopath as infopath
import pin.nodes as nodes
import pin.ui as ui

parser = argparse.ArgumentParser(
        description='Read documentation in Info format',
        epilog='The first non-option argument, if present, is the menu entry '
        'to start from; it is searched for in all \'dir\' files along the '
        'infopath. If it is not present, info merges all \'dir\' file and '
        'shows the result. Any remaining arguments are treated as the names '
        'of menu items relative to the initial node visited.')
parser.add_argument('-a', '--all', action='store_true',
                    help='use all matching manuals')
parser.add_argument('-k', '--apropos', metavar='STRING',
                    help='Look up %(metavar)s in all indices of all manuals')
parser.add_argument('-f', '--file', action='extend', metavar='MANUAL',
                    help='specify INFO manual to visit')
parser.add_argument('-i', '--index-search', metavar='STRING',
                    help='go to node pointed by index entry %(metavar)s')
parser.add_argument('-n', '--node', action='extend', metavar='NODENAME',
                    help='specify nodes in first visited Info file')
parser.add_argument('-o', '--output', metavar='FILE',
                    help='output selected nodes to %(metavar)s')
parser.add_argument('-O', '--show-options', '--usage', action='store_true',
                    help='go to command-line options node')
parser.add_argument('--subnodes', action='store_true',
                    help='recursively output menu items')
parser.add_argument('-w', '--where', '--location',
                    help='print physical location of Info file')
parser.add_argument('pos', nargs='*', action='extend', metavar='MENU-ITEM')
args = parser.parse_args()

# References to the nodes to start the session with.
refs: set[nodes.reference] = set()


def get_initial_file() -> nodes.InfoFile:
    """Find the first file to load.

    May also find the first node to load as well. If the --file option is
    given, use that as the file, otherwise try to interpret the first
    non-option argument, either by looking it up as a dir entry, looking for a
    file by that name, or finding a man page by that name.
    """
    if args.file:
        return args.file[0]
    elif args.node:
        return args.node[0]
    elif args.where:
        return args.where


def parse_menu_item(item: str) -> typing.Union[str, dict[str, str]]:
    """Parse an item input by user.

    If it is not of the form '(arst)arst' then return the plain string.
>>> parse_menu_item('bash')
    'bash'
>>> parse_menu_item('(bash)Bash Variables')
    {'file': 'bash', 'node': 'Bash Variables'}
    """
    if item[0] == '(':
        m = nodes.menu_item_r.match(item)
        if m is not None:
            filename = m.group('file')
            nodename = m.group('node')
            return m.groupdict()
    return item


if __name__ == '__main__':
    # All info files will be viewed as strings at this point and will be
    # processed into InfoPath objects at the initialization of our session.
    # This is simply due to the reference class being very simple, being a
    # strict translation of the C struct found in GNU Info. It doesn't make any
    # sense to start up classes when the data won't be passed on to our
    # session.

    # Scan through the arguments go generate a list of references to load.
    initial_file = get_initial_file()
    for f in args.file:
        ref = nodes.reference()
        ref.filename = f
        refs.add(ref)

    for n in args.node + args.pos:
        # If node is not in long format then search for it in the initial
        # loaded file.
        node_arg = parse_menu_item(n)
        if isinstance(node_arg, str):
            filename = initial_file
            nodename = node_arg
        else:
            filename = node_arg['file']
            nodename = node_arg['node']
        ref = nodes.reference()
        ref.filename = filename
        ref.nodename = nodename
        refs.add(ref)

    session = ui.InfoSession(refs)
    session.run()
