
"""test_nodes.py -- Unit tests for info parsing."""

import unittest
import textwrap

from pin import nodes


class TestNode(unittest.TestCase):
    """Test various constructs found within a node."""

    def test_first_line(self):
        """Parse the first line of a node."""
        m = nodes.NODE_HEADER_R.match(
                'File: sample.info,  Node: Top,  Next: Invoking sample,  Up: '
                '(dir)')
        self.assertEqual(m['filename'], 'sample.info')
        self.assertEqual(m['nodename'], 'Top')
        self.assertEqual(m['next'], 'Invoking sample')
        self.assertIs(m['prev'], None)
        self.assertEqual(m['up'], '(dir)')

        # These have spaces in them
        m = nodes.NODE_HEADER_R.match(
                'File: diffutils.info, Node: Blank Lines, Next: Specified '
                'Lines, Previous: White Space, Up: Comparison')
        self.assertEqual(m['filename'], 'diffutils.info')
        self.assertEqual(m['nodename'], 'Blank Lines')
        self.assertEqual(m['next'], 'Specified Lines')
        self.assertEqual(m['prev'], 'White Space')
        self.assertEqual(m['up'], 'Comparison')

        # This shouldn't normally happen, but say some are missing along with
        # incorrect capitalization.
        m = nodes.NODE_HEADER_R.match(
                'File: diffutils.info, node: Incomplete Lines, prev: '
                'Output Formats, Up: If-then-else')
        self.assertEqual(m['filename'], 'diffutils.info')
        self.assertEqual(m['nodename'], 'Incomplete Lines')
        self.assertIs(m['next'], None)
        self.assertEqual(m['prev'], 'Output Formats')
        self.assertEqual(m['up'], 'If-then-else')

    def test_x(self):
        """Get a single cross reference in our node."""
        # Watch out for new lines.
        # x_label = 'for the complete contents of the files'
        x_text = '(*note Sample\n\tdiff3 input::)'
        xref = nodes.XReference(x_text).refs[0]
        self.assertEqual(xref.nodename, 'Sample diff3 input')

        # Test the alternate format
        x_node = 'Emerge'
        x_file = 'emacs'
        x_text = f"*note {x_node}: ({x_file}){x_node},"
        xref = nodes.XReference(x_text).refs[0]
        self.assertEqual(xref.filename, 'emacs')
        self.assertEqual(xref.nodename, 'Emerge')

    def test_menu(self):
        """Get a menu items in our node."""
        menu_text = textwrap.dedent("""
        * Menu:
        * Tabs::            Preserving the alignment of tab stops.
        * Trailing Blanks:: Suppressing blanks before empty output lines.
        * Pagination::      Page numbering and time-stamping 'diff' output.
        """)
        menu = nodes.Menu(menu_text).refs
        self.assertEqual(len(menu), 3)
        self.assertEqual(menu[0].nodename, 'Tabs')
        self.assertEqual(menu[1].nodename, 'Trailing Blanks')
        self.assertEqual(menu[2].nodename, 'Pagination')

    def test_index(self):
        """Get index items in our node."""
        index_text = textwrap.dedent(
        """
        \x00\x08[index\x00\x08]
        * Menu:

        * ! output format:          Context.        (line 6)
        * +x output format:         Unified Format. (line 6)
        * < output format:          Normal.         (line 6)
        * pebibyte, definition of:  cmp Options.
                                                    (line 97)
        """)
        indicies = nodes.Index(index_text).refs
        self.assertEqual(len(indicies), 4)

        self.assertEqual(indicies[0].label, '! output format')
        self.assertEqual(indicies[0].nodename, 'Context')
        self.assertEqual(indicies[0].line_number, 6)

        self.assertEqual(indicies[1].label, '+x output format')
        self.assertEqual(indicies[1].nodename, 'Unified Format')
        self.assertEqual(indicies[1].line_number, 6)

        self.assertEqual(indicies[2].label, '< output format')
        self.assertEqual(indicies[2].nodename, 'Normal')
        self.assertEqual(indicies[2].line_number, 6)

        self.assertEqual(indicies[3].label, 'pebibyte, definition of')
        self.assertEqual(indicies[3].nodename, 'cmp Options')
        self.assertEqual(indicies[3].line_number, 97)


class TestFileBuffer(unittest.TestCase):
    """Test the code on a tiny info file."""

    def setUp(self):
        """Load sample.info."""
        self.file = nodes.InfoFile('test/sample.info')
        self.buffer = nodes.FileBuffer(self.file)

    def test_name(self):
        """Check the name of our buffer."""
        self.assertEqual(self.buffer.filename, 'sample.info')

    def test_tags(self):
        self.assertEqual(len(self.buffer.tags), 4)
        self.assertEqual(self.buffer.tags[0].nodename, 'Top')
        self.assertEqual(self.buffer.tags[0].nodestart, 801)
        self.assertEqual(self.buffer.tags[1].nodename, 'Invoking sample')
        self.assertEqual(self.buffer.tags[1].nodestart, 1061)
        self.assertEqual(self.buffer.tags[2].nodename, 'GNU Free '
                'Documentation License')
        self.assertEqual(self.buffer.tags[2].nodestart, 1349)
        self.assertEqual(self.buffer.tags[3].nodename, 'Index')
        self.assertEqual(self.buffer.tags[3].nodestart, 1542)

    def test_nodes(self):
        """Test the nodes for correct headers, and cross-references.

        Only the first and last nodes are checked. There aren't any
        cross-references in the sample info file, but that shouldn't be
        necessary.
        """
        # This should preserve the correct order of nodes if you aren't using
        # old-ass python.
        node_list = list(self.buffer.nodes.values())
        first_node = node_list[0]
        last_node = node_list[-1]

        self.assertEqual(first_node.name, 'Top')
        self.assertTrue(first_node.contents)
        self.assertEqual(first_node.prev, '')
        self.assertEqual(first_node.next, 'Invoking sample')
        self.assertEqual(first_node.up, '')
        self.assertEqual(len(first_node.references), 3)
        self.assertEqual(first_node.references[0].nodename, 'Invoking sample')
        self.assertEqual(first_node.references[1].nodename,
                'GNU Free Documentation License')
        self.assertEqual(first_node.references[2].nodename, 'Index')

        self.assertEqual(last_node.name, 'Index')
        self.assertTrue(last_node.contents)
        self.assertEqual(last_node.next, '')
        self.assertEqual(last_node.prev, 'GNU Free Documentation License')
        self.assertEqual(len(last_node.references), 2)
        self.assertEqual(last_node.references[0].nodename, 'Invoking sample')
        self.assertEqual(last_node.references[0].line_number, 6)
        self.assertEqual(last_node.references[0], last_node.references[1])
        self.assertEqual(last_node.references[0].label, 'invoking sample')
        self.assertEqual(last_node.references[1].label, 'sample')
