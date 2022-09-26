
"""ui.py -- The interface given to the user."""

import curses
import typing
from collections import ChainMap
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import PosixPath

from pin import nodes

# I wanted to put the arrow keys in a separate dict, but chainmaps cannot be
# put within chainmaps.
hard_coded_keys = {
        curses.KEY_LEFT: 'backward-char',
        curses.KEY_UP: 'prev-line',
        curses.KEY_DOWN: 'next-line',
        curses.KEY_RIGHT: 'forward-char',
        curses.KEY_DC: 'scroll-backward',
        curses.KEY_BTAB: 'move-to-prev-xref',
        curses.KEY_ENTER: 'select-reference-this-line'
        }

# These are copied verbatim from the info manual. There is currently no planned
# support for the meta key and some of the functions may not be defined. Input
# that is only valid in Windows is simply undefined. Many of the inputs that
# GNU Info detects can't be here because there is no support for alt keys or
# a sequence of keys.
# The only implemented cross reference commands are moving and selection.
# Many of the miscellanious commands that self-document GNU Info aren't
# implemented either.
original_keys = {
        '^n': 'next-line',
        '^p': 'prev-line',
        '^a': 'beginning-of-line',
        '^e': 'end-of-line',
        '^f': 'forward-char',
        '^b': 'backward-char',
        'M-f': 'forward-word',
        'M-b': 'backword-word',
        'M-<': 'beginning-of-node',
        'M->': 'end-of-node',
        'M-r': 'move-to-window-line',
        ' ': 'scroll-forward',
        '^v': 'scroll-forward-page-only',
        'M-v': 'scroll-backward-page-only',
        'n': 'next-node',
        'p': 'prev-node',
        'u': 'up-node',
        'l': 'history-node',
        't': 'top-node',
        'd': 'dir-node',
        '<': 'first-node',
        '>': 'last-node',
        ']': 'global-next-node',
        '[': 'global-prev-node',
        'g': 'goto-node',
        'O': 'goto-invocation',
        'G': 'menu-sequence',
        '^x^f': 'view-file',
        '^x^b': 'list-visited-nodes',
        '^xb': 'selected-visited-node',
        's': 'search',
        '/': 'search',
        '?': 'search-backword',
        '^xn': 'search-next',
        '}': 'search-next',
        '^xN': 'search-previous',
        '{': 'search-previous',
        'R': 'toggle-regexp',
        'S': 'search-case-sensitively',
        '^s': 'isearch-forward',
        '^r': 'isearch-backward',
        'M-/': 'tree-search',
        'M-}': 'tree-search-next',
        'M-{': 'tree-search-previous',
        'i': 'index-search',
        'I': 'virtual-index',
        ',': 'next-index-match',
        # Not sure if this is right
        '\t': 'move-to-next-xref',
        '^xo': 'next-window',
        'M-x': 'prev-window',
        '^x0': 'delete-window',
        '^x1': 'keep-one-window',
        'h': 'get-info-help-node',
        '=': 'display-file-info',
        '^g': 'abort-key',
        }

# The echo area should simply use python's readline, but we'll put it
# here for completeness. Combinations of the meta key with special characters
# are not supported; I can't figure out where the LEFT_ALT_PRESSED macro is
# defined.
echo_keys = {
        '^f': 'echo-area-forward',
        '^b': 'echo-area-backword',
        '^a': 'echo-area-beg-of-line',
        '^e': 'echo-area-end-of-line',
        'M-f': 'echo-area-forward-word',
        'M-b': 'echo-area-backward-word',
        '^d': 'echo-area-delete',
        '^g': 'echo-area-abort',
        '^q': 'echo-area-quoted-insert',
        '^t': 'echo-area-transpose-chars',
        'M-d': 'echo-area-kill-word',
        '^k': 'echo-area-kill-line',
        '^y': 'echo-area-yank',
        'M-y': 'echo-area-yank-pop',
        '\t': 'echo-area-complete'
        }

vi_keys = {
        'g': 'first-node',
        'G': 'last-node',
        'M-b': 'beginning-of-node',
        'M-e': 'end-of-node',
        'j': 'next-line',
        'k': 'prev-line',
        'f': 'scroll-forward-page-only',
        '^f': 'scroll-forward-page-only',
        'M-\\': 'scroll-forward-page-only',
        'z': 'scroll-forward-page-only',
        'b': 'scroll-backward-page-only',
        '^b': 'scroll-backward-page-only',
        '\\kd': 'down-line',
        '^e': 'down-line',
        '^j': 'down-line',
        '^m': 'down-line',
        '\\ku': 'up-line',
        '^y': 'up-line',
        '^k': 'up-line',
        'd': 'scroll-half-screen-down',
        '^d': 'scroll-half-screen-down',
        'u': 'scroll-half-screen-up',
        '^u': 'scroll-half-screen-up',
        '^xn': 'next-node',
        '^xp': 'prev-node',
        '^xu': 'up-node',
        '\'': 'last-node',
        'M-t': 'top-node',
        'M-d': 'dir-node',
        '^xg': 'goto-node',
        'I': 'goto-invocation-node',
        'n': 'search-next',
        'N': 'search-previous',
        'M-f': 'xref-item',
        '^xr': 'xref-item',
        'M-g': 'select-reference-this-line',
        '^x^j': 'select-reference-this-line',
        '^x^m': 'select-reference-this-line',
        '^c': 'abort-key',
        'M-h': 'get-info-help-node',
        ':q': 'quit',
        'ZZ': 'quit'
        }


default_keys = {
        'g': 'beginning-of-node',
        'G': 'end-of-node',
        'j': 'next-line',
        'k': 'prev-line',
        'f': 'scroll-forward-page-only',
        '^f': 'scroll-forward-page-only',
        'b': 'scroll-backward-page-only',
        '^b': 'scroll-backward-page-only',
        '\\kd': 'down-line',
        '^e': 'down-line',
        '^j': 'down-line',
        '\\ku': 'up-line',
        '^y': 'up-line',
        '^k': 'up-line',
        'd': 'scroll-half-screen-down',
        '^d': 'scroll-half-screen-down',
        'u': 'scroll-half-screen-up',
        '^u': 'scroll-half-screen-up',
        '>': 'next-node',
        '<': 'prev-node',
        'n': 'search-node',
        'N': 'search-previous',
        '^c': 'abort-key',
        ':h': 'get-info-help-node',
        ':q': 'quit',
        'ZZ': 'quit'
        }


@dataclass
class WindowState:
    """An entry in the history index."""

    node: nodes.Node
    page_top: int
    point: int

@dataclass
class LineMap():
    """
    A line map structure keeps a list of points that given a line will map a
    column number to the point number. It is used to convert point values into
    columns on screen and vice versa.
    """
    node: Node
    nline: int = 0
    offsets: typing.List[int] = []

    def __len__(self):
        return len(self.offsets)

    def __getitem__(self, index):
        return self.offsets[index]

class InfoWindow:
    """Manage the user interface for a single file.

    Each window will have all alphatebical letters as marks for the user to
    assign to.
    """

    def __init__(self, node):
        """Node content-specific TUI parameters."""
        self._node = node
        self.pad = curses.newpad(node.contents.count('\n'), 80)
        self._page_top: int = 0
        self.point: int = 0
        self.goal_column = -1
        self.hist: typing.List[WindowState] = [WindowState(node, 0, 0)]
        self.line_count = node.content.count('\n') + 1
        self.line_starts: typing.List[int] = []
        self.line_map: LineMap

    @property
    def node(self):
        """Node that the window currently displays."""
        return self._node

    @node.setter
    def node(self, value):
        self._node = value
        self._calculate_line_starts()
        self.page_top = 0
        self.point = 0
        self._refresh()

    @property
    def line_count(self) -> int:
        pass

    @property
    def page_top(self) -> int:
        """First line shown in the window.

        Effectively the user's current location within a node.
        """
        return self._page_top

    @page_top.setter
    def page_top(self, desired):
        """Set the page_top, perhaps scrolling the screen to do so."""
        if desired < 0:
            desired = 0
        elif desired > self.line_count:
            desired = self.line_count - 1

        if self.page_top == desired:
            return

        old_pt = self.page_top
        # Make sure that point appears in this window
        point_line = self.line_of_point()
        if point_line < self.page_top:
            self.point = self.line_starts[self.page_top]
        else:
            if point_line < self.page_top + self.height:
                return
            bottom = self.page_top + self.height - 1
            self.point = self.line_starts[bottom]

        # Find out which direction to scroll. Do this only if there would be
        # savings in refresh time. This is true if the amount to scroll is less
        # than the height of the window, and if the number of lines scrolled
        # would be greater than 10% of the window's height

        # To prevent status line blinking when keeping the up or down key,
        # scrolling is disabled if the amount to scroll is 1.

        if old_pt < desired:
            amount = desired - old_pt
            if (amount == 1 or amount >= self.height or
                    (self.height - amount)*10 < self.height):
                return
            start = self.first_row()
            end = start + self.height

            # window_scroll
        else:
            amount = old_pt - desired
            if (amount == 1 or amount >= self.height or
                    (self.height - amount)*10 < self.height):
                return
            start = self.first_row()
            end = start + self.height



        self.scr.refresh()

    @property
    def cursor_column(self):
        return self.point := self.point_to_column(self.point)

    def _calculate_line_starts(self):
        """Calculate a list of line starts for the current node."""
        c = 0
        for line in self.node.contents.splitlines(True):
            self.line_starts.append(c)
            c += len(line)

    # TODO: Support wide characters.
    def _compute_line_map(self):
        """Compute the line map for the current line in our window."""
        line = self.line_of_point()
        if (self.life_map.node == self.node and self.line_map.nline == line and
                self.line_map.used):
            return
        self.line_map = LineMap(self.node)
        self.line_map.node = self.node
        self.line_map.nline = line
        
        if line + 1 < self.line_count:
            endi = self.node.contents + self.line_starts[line + 1]
        else:
            endi = self.node.contents + len(self.node)
        
        for i,c in enumerate(self.node.contents[self.line_starts[line]:]):
            self.line_map.offsets.append(i + self.line_starts[line])

    def _refresh(self):
        self.pad.refresh(self.page_top, 0, 0, 0, self.height, self.width)

    def line_of_point(self) -> int:
        """Line containing self.point."""
        return next(i-1 for i, o in enumerate(self.line_starts) if o >=
                    self.point)

    def point_to_column(self, point: int) -> int:
        """Tranlate the value of a point into a column number."""
        self._compute_line_map()
        if (point < self.line_map.offsets[0]):
            return 0
        return next(i for i,o in enumerate(self.line_map.offsets) if o >= point)

    def first_row(self):
        """Offset for the line of point."""
        return self.line_starts(self.page_top)

    def make_modeline(self):
        """

        Copied from gnu Info."""
        # Find the number of lines actually displayed in this window
        lines_remaining = self.line_count - self.state.page_top
        if self.state.page_top == 0:
            if lines_remaining <= self.height:
                location_indicator = 'All'
            else:
                location_indicator = 'Top'
        else:
            if lines_remaining <= self.height:
                location_indicator = 'Bot'
            else:
                lc = self.line_count - self.height
                percent = 100*self.state.page_top/lc
                location_indicator = "{2f}%".format(percent)

        # Calculate the maximum size of the information to stick in modeline
        name = self.state.node.filename.split('.')[0]
        # Remove the parentheses and you get a syntax error
        mode = (f"-----Info: ({name}){self.state.node}, " +
                f"{self.line_count} lines --{location_indicator}")
        mode += '-'*(self.width - len(mode))

    def goto_percentage(self, percent: int):
        """Make window display at given percentage of the node."""
        if percent <= 0:
            desire = 0
        if percent >= 100:
            desire = self.line_count

        self.page_top = desire
        self.point = self.line_starts[self.page_top]
        self.make_modeline()

    def point_next_line(self):
        """Advance point to the beginning of the next logical line.

        Also compute line map of new line.
        """
        line = self.line_of_point()
        self.point = self.line_starts[line + 1]
        self._compute_line_map()

    def point_prev_line(self):
        """Move point to the end of the previous logical line.

        Also compute line map of new line.
        """
        line = self.line_of_point()
        self.point = self.line_starts[line - 1]
        self._compute_line_map()

    def move_to_goal(self):
        if self.goal_column >= len(self.line_map):
            goal = len(self.line_map) - 1
        self.point = self.line_map.offsets[self.goal_column]
        self.show_point()

    def adjust_pagetop(self):
        """Adjust page_top such that the cursor will be visible."""

        line = self.line_of_point()
        # If this line appears in the current displayable page, do nothing.
        # Otherwise, adjust the top of the page to make this line visible.
        if line < self.page_top or line - self.page_top > self.height - 1:
            pt_center = line - (self.height - 1) // 2
            self.page_top = 0 if pt_center < 0 else pt_center

    def show_point(self):
        """Scroll window so that point is visible & move terminal cursor there.

        Used after cursor movement commands.
        """
        self.adjust_pagetop()
        self.display_cursor_at_point()

    def message_echo_area(self, fstr: str, *args):
        """Populate the echo area.

        If there's already a message appearing in the echo area, then it is
        removed.
        """
        pass


class InfoSession:
    """Each session can have up to 10 windows."""

    def __init__(self, refs: typing.Set[nodes.Reference]):
        """Load settings and start up curses."""
        self.refs = refs
        self.loaded_buffers: dict[str, nodes.FileBuffer] = {}
        self.windows: typing.List[InfoWindow] = []
        try_strings = (
                '~/.pin.ini',
                '~/.config/pin/pin.ini',
                )
        try_paths = map(lambda x: PosixPath(x).expanduser(), try_strings)
        config_file = next(p for p in try_paths if p.exists())
        self.config = ConfigParser()
        self.config.read(config_file)
        self.input_map = ChainMap(
                default_keys, hard_coded_keys, self.config['keys'])
        for r in refs:
            new_buf = nodes.FileBuffer(nodes.InfoFile(PosixPath(r.filename)))
            self.loaded_buffers[r.filename] = new_buf
            self.windows.append(InfoWindow(new_buf.nodes[r.nodenode]))
        self.scr = curses.init
        self.height, self.width = self.scr.getmaxyx()
        curses.cbreak()
        curses.noecho()

    # Ugh. I'm sick of this. I really ought to just use prompt-toolkit instead
    # of directly using curses. However there's no way to remap the vi mappings
    # so I'm done with this until that other thing's fixed.
    # Or you can just rewrite it all in Go.
    def run(self):
        """Run this session."""
        while True:
            raw_key = curses.getch()
            if 48 <= raw_key <= 57:
                self.cur_window = self.windows[int(chr(raw_key))]
            elif raw_key in hard_coded_keys:
                pass
            else:
                action = keys[curses.keyname(raw_key)]
                match action:
                    # Unfortunately we have no control over how a varible is
                    # treated (i.e. as a variable or a reference), so there's
                    # no way to shorten much of this code.
                    case 'first-node':
                        self.cur_window.node =
                        self.cur_window.node.file_buffer.nodes[0]
                    case 'last-node':
                        self.cur_window.node =
                        self.cur_window.node.file_buffer.nodes[-1]
                    case 'beginning-of-node':
                        self.cur_window.page_top = 0
                    case 'end-of-node':
                        self.cur_window.page_top = self.cur_window.pad.rows -
                        self.height
                    case 'next-line':
                        if self.cur_window.goal_column == -1:
                            self.cur_window.goal_column =
                                self.cur_window.cursor_column
                        self.cur_window.point_next_line()
                        self.cur_window.move_to_goal()
                    case 'prev-line':
                        if self.cur_window.goal_column == -1:
                            self.cur_window.goal_column =
                                self.cur_window.cursor_column
                        self.cur_window.point_prev_line()
                        self.cur_window.move_to_goal()
                    case 'beginning-of-line':
                        point = self.cur_window.line_map[0]
                        if point != self.cur_window.point:
                            self.cur_window.point = point
                            self.show_point()
                    case 'end-of-line':
                        point = self.cur_window.line_map[-1]
                        if point != self.cur_window.point:
                            self.cur_window.point = point
                            self.cur_window.show_point()
                    case 'scroll-forward-page-only':
                        self.cur_window.page_top += self.height
                    case 'scroll-backward-page-only':
                        self.cur_window.page_top -= self.height
                    case 'down-line':
                        self.cur_window.page_top += 1
                    case 'up-line':
                        self.cur_window.page_top -= 1
                    case 'scroll-half-screen-down':
                        self.cur_window.page_top += self.height // 2
                    case 'scroll-half-screen-up':
                        self.cur_window.page_top -= self.height // 2
                    case 'next-node' if self.cur_window.node.next:
                        self.cur_window.node =
                        self.cur_window.file_buffer.nodes[
                                self.cur_window.node.next]
                    case 'prev-node' if self.cur_window.node.prev:
                        self.cur_window.node =
                        self.cur_window.file_buffer.nodes[
                                self.cur_window.node.prev]
                    case 'global-next-node':
                        self.cur_window.node =
                        self.cur_window.node.file_buffer.after(
                                self.cur_window.node)
                    case 'global-prev-node':
                        self.cur_window.node =
                        self.cur_window.node.file_buffer.before(
                                self.cur_window.node)
                    case 'up-node':
                        self.cur_window.node =
                        self.cur_window.node.file_buffer.before(
                                self.cur_window.up)
                    case 'history-node':
                        pass
                    case 'top-node':
                        pass
                    case 'dir-node':
                        pass
                    case 'goto-node':
                        pass
                    case 'goto-invocation':
                        pass
                    case 'list-visited-nodes':
                        pass
                    case 'search':
                        pass
                    case 'search-backword':
                        pass
                    case 'search-next':
                        pass
                    case 'search-previous':
                        pass
                    case 'toggle-regexp':
                        pass
                    case 'search-case-sensitively':
                        pass
                    case 'isearch-forward':
                        pass
                    case 'isearch-backward':
                        pass
                    case 'tree-search':
                        pass
                    case 'tree-search-next':
                        pass
                    case 'tree-search-previous':
                        pass
                    case 'index-search':
                        pass
                    case 'virtual-index':
                        pass
                    case 'next-index-match':
                        pass
                    case 'index-apropos':
                        pass
                    case 'move-to-next-xref':
                        pass
                    case 'move-to-prev-xref':
                        pass
                    case 'select-reference-this-line':
                        pass
                    case 'abort-key':
                        pass
