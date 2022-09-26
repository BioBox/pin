
# A vim-like info reader

**pin** is a vim-like texinfo reader written in python, with the code being
heavily inspired by the browser found in the original `texinfo` package.
Currenly the only package in use is [regex][regex] although **the project is
currently unfinished**. At some point a user interface made using
[prompt-toolkit][prompt] would be nice, but I simply don't have the time to
finish it. I might actually rewrite this in a lower level language such as Go
so that I don't have to wrestle with prompt-toolkit[^1]. It is heavily based on
the browser that comes with the texinfo package, but only the core parser is
implemented.

You can run the tests using `python -m unittest discover`, but be warned that
**you must use 3.10** or above.

## Contributing

It's unlikely I'll ever finish this, but contributions are welcome. I only
require that you run the unittests and check your code using pylint.

[regex]: https://github.com/mrabarnett/mrab-regex
[prompt]: https://github.com/prompt-toolkit/python-prompt-toolkit

[^1]: It's really good, but lacks the degree of flexibility that I want out of
  my ui.
