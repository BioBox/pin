
"""nodes.py -- Manage files and the nodes that are loaded from them."""

# This module also parses the Info Format Specification, so it's recommended to
# have a look at Appendix F of the GNU Texinfo manual before reading.

import abc
import enum
import os
import typing
from dataclasses import dataclass
from pathlib import PosixPath
from subprocess import run
from itertools import islice

import regex as re

from pin import utils
from pin import infopath

INFO_COOKIE = '\037'
INFO_FF = '\014'
NL_SEP = r',\s+'
NL_C = '[^,\n]+'  # Contents
NODE_RAW = ''.join((fr"^File:\s+(?P<filename>{NL_C}){NL_SEP}",
                    fr"Node:\s+(?P<nodename>{NL_C})",
                    fr"({NL_SEP}Next:\s+(?P<next>{NL_C}))?",
                    fr"({NL_SEP}Prev(ious)?:\s+(?P<prev>{NL_C}))?",
                    fr"({NL_SEP}Up:\s+(?P<up>{NL_C}))?$"))

NODE_SEP = f"^{INFO_COOKIE}{INFO_FF}?\r?$"
SEP_R = re.compile(NODE_SEP, re.MULTILINE | re.IGNORECASE)
NODE_HEADER_R = re.compile(NODE_RAW, re.MULTILINE | re.IGNORECASE)

TAG_TABLE_ENTRY = 'Node: (?P<name>[\\w ]+)\x7F(?P<num>\\d+)'
TTE_R = re.compile(TAG_TABLE_ENTRY, re.IGNORECASE)

# Non-empty line stripped of whitespace
line_r = re.compile(r'^\s*(\S.*?)\s*$', re.MULTILINE)
menu_item_r = re.compile(r'\((?P<file>\w+)\)(?P<node>\w+)')

compress_suffixes = {
        '.gz': ['gzip', '-d'],
        '.lz': ['lzip', '-d'],
        '.xz': ['unxz'],
        '.bz2': ['bunzip2'],
        '.z': ['uncompress'],
        '.Y': ['unyabba']
}


# Since an enumeration cannot have a non-empty parent, we will simply build a
# completely seperate one using the functional API. Mypy doesn't like this, but
# it's completely valid code.
class Labels(enum.Enum):
    """Labels for points of interest in an info file."""
    TABLE_BEG = 'Tag Table:'
    TABLE_END = 'End Tag Table:'
    MENU = '\n* Menu:'
    XREF = '*Note'
    MENU_ENTRY = '\n* '


@dataclass
class Tag:
    """A pointer to a node in an info file.

    For each logical file that we have loaded, we keep a list of the names
    of the nodes that are found in that file. A pointer to a node in an info
    file is called a "tag".
    :param filename:        The file where this node can be found
    :param nodename:        The node pointed to by this tag
    :param nodestart:       The value read from the tag table
    """

    filename: str
    nodename: str
    nodestart: int = -1
    # cache: Node = None              # Saved information about pointed-to node


@dataclass(init=False)
class Reference:
    """Structure which describes a node reference (possibly invalid)."""

    filename: str
    nodename: str
    label: str
    start: int
    end: int
    line_number: int

    def __eq__(self, other):
        """Compare the file name and node name."""
        return (self.filename == other.filename and
                self.nodename == other.nodename)

    def __hash__(self):
        """Derive from eq."""
        return hash(self.filename) ^ hash(self.nodename)


class InfoFile(infopath.IPath):
    """A path object for an info file."""

    @staticmethod
    def _check_compressed(path: PosixPath) -> typing.Optional[PosixPath]:
        """Check for compression suffixes to help validate an info file.

        Returns successful on no extension as well.
        """
        if path.is_file():
            return path
        for suffix in compress_suffixes:
            try_c = path.with_suffix(suffix)
            if try_c.is_file():
                return try_c
        return None

    @staticmethod
    def _check_info(path: PosixPath) -> PosixPath:
        """Validate an info file."""
        try_paths = iter((path.joinpath('index'),
                         InfoFile._check_compressed(path),
                         InfoFile._check_compressed(path.with_suffix(
                             '.info'))))
        for p in try_paths:
            if p:
                return p
        raise FileNotFoundError

    def __init__(self, path: typing.Union[str, PosixPath]):
        """Find the file that path points to."""
        self._path = infopath.IPath(path)

        if self._path.is_file():
            super().__init__(path)
        else:
            for d in infopath.infodirs:
                try:
                    super().__init__(InfoFile._check_info(d / self._path.name))
                except TypeError:
                    pass
                else:
                    self.is_compressed = bool(self.compression_suffix)
                    return
            raise FileNotFoundError(f"Cannot find info file {path}")

    @property
    def compression_suffix(self):
        """Return suffix if it is of a proper compression type."""
        if self.suffix in compress_suffixes:
            return self.suffix
        return None

    @property
    def finfo(self) -> os.stat_result:
        """Return the stat of file."""
        return self._path.stat()

    @property
    def filesize(self):
        """Return the size of the file taken from finfo."""
        return self.finfo.st_size


class FileBuffer:
    """Represent a loaded info file.

    Remember information about the contents of info files that we have
    loaded at least once before. The :param:`finfo` member is present so that
    we can reload the file if it has been modified since last being loaded.
    :param filename: The filename used to find this file
    :param fullpath: The full pathname of this info file
    :param contents: The contents of this particular file
    :param tags: The tags table
    """

    @dataclass
    class _SubFile:
        filename: str
        first: int

    def _read_info_file(self):
        suffix = self._path.compression_suffix
        if suffix:
            self.contents = run(compress_suffixes[suffix] + [str(self._path)],
                       check=True).stdout
        else:
            with open(self.fullpath, 'r') as f:
                self.contents = f.read()

    @property
    def filename(self):
        """Return basename."""
        return self._path.name

    @property
    def fullpath(self) -> str:
        """Return full path."""
        return str(self._path.resolve())

    def __init__(self, path: InfoFile):
        """Load an info file from a given path."""

        self.flags = 0
        self.tags: typing.List[Tag] = []
        self.nodes = utils.DList()
        self._path = InfoFile(path)

        self._read_info_file()
        self._scan_tags_table()
        self._build_nodes()

    def _scan_tags_table(self):
        """Build the nodes of the buffer by scaning for a tags table.

        This is used for both direct and indirect tables.
        """
        for sep in SEP_R.finditer(self.contents, len(self.contents)-1000):
            table_iter = line_r.finditer(self.contents, sep.end())
            label = next(table_iter)
            if label.group(1) == Labels.TABLE_BEG.value:
                for entry in table_iter:
                    e = entry.group(1)
                    m = TTE_R.fullmatch(e)
                    if m is None:
                        return
                    new_tag = Tag(self.filename, m.group('name'))
                    new_tag.nodestart = int(m.group('num'))
                    self.tags.append(new_tag)

    def _build_nodes(self):
        """Build the list of nodes from the tag table."""
        for t in self.tags:
            self.nodes[t.nodename] = Node(self, t)


class ReferenceHooks(enum.Enum):
    """Regular expressions that signify the beginning of a reference source."""

    # INDEX must include the menu part, otherwise INDEX and MENU will both
    # match and lastindex will give the wrong number.
    INDEX = '\x00\x08\\[index\x00\x08\\]\\s*^\\* Menu:'
    MENU = r'^\* Menu:'
    X_REF = r'\* Note:'


class ReferenceSource(abc.ABC):
    """Abstract base class for sources of references."""

    # This method should be a property as well, but a property cannot also be a
    # class method, so we'll perform a bit of metaprogramming with
    # __init_subclass__ introduced in v3.6
    @classmethod
    @abc.abstractmethod
    def _regex(cls) -> re.Pattern:
        """Extract the contents (abstract)."""

    def add_ref(self, ref_obj: typing.Union[re.Match, Reference], offset=0):
        """Add a reference to this source."""
        if isinstance(ref_obj, re.Match):
            gd = ref_obj.groupdict()
            ref = Reference()
            ref.filename = gd.get('file', '')
            ref.nodename = re.sub(r'[\t\s]+', ' ', gd['name'])
            ref.start = ref_obj.start('name') + offset
            ref.end = ref_obj.end('name') + offset
        elif isinstance(ref_obj, Reference):
            ref = ref_obj
        else:
            raise TypeError('m must be a match object or reference.')
        self.refs.append(ref)

    def __init__(self, din: str):
        """Scan the contents using regex."""
        self.refs: typing.List[Reference] = []
        self._matches = list(self._regex().finditer(din))
        for m in self._matches:
            self.add_ref(m)

    def __init_subclass__(cls):
        """Assign the abtract class property."""
        cls.regex = cls._regex()


class Menu(ReferenceSource):
    """Node menu as a reference source.

    This only handles the simplified double colon form of the entries. I'm not
    using the other one because it's superfluous complexity.
    """

    __regex = re.compile(r'^\* (?P<name>\w[\w ]*)::', re.MULTILINE)

    @classmethod
    def _regex(cls):
        """Extract the contents (menu)."""
        return cls.__regex

class Index(ReferenceSource):
    """The index section as a reference source."""

    __regex = re.compile(r'\s+'.join((
        r'^\*',
        r'(?P<label>[^:]+):',
        r'(?P<name>[\w ]+)\.',
        r'\(line (?P<line>[\d]+)\)')), re.MULTILINE)

    @classmethod
    def _regex(cls):
        return cls.__regex

    def add_ref(self, ref_obj: typing.Union[re.Match, Reference], offset=0):
        """Add a reference to this source with the line number."""
        if isinstance(ref_obj, re.Match):
            gd = ref_obj.groupdict()
            ref = Reference()
            ref.filename = gd.get('file', '')
            ref.nodename = gd['name']
            ref.label = gd['label']
            ref.line_number = int(ref_obj['line'])
            ref.start = ref_obj.start('name') + offset
            ref.end = ref_obj.end('name') + offset
        elif isinstance(ref_obj, Reference):
            ref = ref_obj
        else:
            raise TypeError('m must be a match object or reference.')
        self.refs.append(ref)


class XReference(ReferenceSource):
    """An inline cross-reference as a reference source."""

    ref_id = '(\\((?P<file>\\w+)\\))?\x7F?(?P<name>[\\w\\s]+)\x7F?'
    label = '\x7F?(\\w+)\x7F?'
    # Unfortunately, we must make multiple regexes to handle the different
    # forms of cross-references; we can't simply say "use the better version".
    # This wouldn't work with python's re builtin because you can't have groups
    # of the same name, which is fine until a single pattern needs to match the
    # same groups in different ways like in this instance.
    _regex1 = f"(?P<name>{ref_id})::"
    _regex2 = f"(?P<label>{label}): {ref_id}[.,]"
    __regex = re.compile(r'\*Note ' + '|'.join((_regex1, _regex2)),
                         re.IGNORECASE)

    @classmethod
    def _regex(cls):
        """Extract the contents (cross ref)."""
        return cls.__regex


class Node:
    """Implement a node."""

    hook = re.compile('|'.join(map(lambda x: '(' + x.value + ')',
        ReferenceHooks.__members__.values())), re.IGNORECASE | re.MULTILINE)

    def __len__(self):
        return len(self.contents)

    def __init__(self, file_buffer: FileBuffer, tag: Tag):
        self.file_buffer = file_buffer
        self.name = tag.nodename
        # These must be strings because we haven't built the node dictionary
        # yet. Whether or not I'll include pointers to it's family I haven't
        # decided yet.
        self.prev: str
        self.next: str
        self.up: str
        self.references: typing.List[Reference] = []
        next_sep = SEP_R.search(file_buffer.contents, tag.nodestart + 1)
        if next_sep is not None:
            nodeend = next_sep.end()
        else:
            raise RuntimeError("Can't find ending node seperator for"
                    f"{self.name}")
        self.contents = file_buffer.contents[tag.nodestart:nodeend]
        self._scan()

    def _scan(self):
        # Read the first line of the node and set next, prev, and up
        header = NODE_HEADER_R.search(self.contents).groupdict('')
        if header:
            self.prev = header['prev']
            self.next = header['next']
            self.up = '' if header['up'] == '(dir)' else header['up']
        else:
            raise RuntimeError(f"Can't find node header for {self.name}")

        # Menu type references will scan from the first line to the second
        # empty line. Cross-references will take the whole thing and return a
        # singleton.
        for m in self.hook.finditer(self.contents):
            match m.lastindex:
                case 1: # ReferenceHooks.INDEX
                    s = m.start()
                    e = next(islice(re.finditer('^$', self.contents[s:], re.M),
                        1, 2)).start() + s
                    source = Index(self.contents[s:e])
                case 2: # ReferenceHooks.MENU
                    s = m.start()
                    e = next(islice(re.finditer('^$', self.contents[s:], re.M),
                        1, 2)).start() + s
                    source = Menu(self.contents[s:e])
                case 3: # ReferenceHooks.X_REF
                    s = m.start()
                    e = m.end()
                    source = XReference(self.contents[s:e])
                case _:
                    raise RuntimeError(f"Can't identify reference {m.group()}")
            self.references.extend(source.refs)
