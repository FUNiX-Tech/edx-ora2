# ORA installation

There are too much version confilictings when running `make install`:pout:

The devstack containers must be running before the following steps (`make dev.up`)

1. Clone edx-ora2

```shell
cd open-edx-foloder/src # the src and devstack folders are located in the same directory
git clone https://github.com/uuuuv/edx-ora2.git
cd edx-ora2
git checkout uuuuv.interface
```

2. Replace the `test.txt` here to `requirements/test.txt`

3. Replace pipy ora with the ora we just cloned

You can do either:

- In the folder `edx-ora2` we just cloned:

```shell
make install-local-ora
```

- In the lms or studio container:

```shell
make dev.shell.lms # or make dev.shell.studio
pip uninstall ora2 -y
pip install -e /edx/src/edx-ora2/
```

4. Install dependencies

This must be done from inside the lms or studio container

```shell
make dev.shell.lms
cd /edx/src/edx-ora2
virtualenv edx-ora2 # must be 'edx-ora2'
source edx-ora2/bin/activate
make install
```

5. Restart lms, studio, see the result

```shell
make lms-restart lms-logs
make studio-restart studio-logs
```

# Bugs

Remember to restart lms, studio after fixing bugs.

### TypeError: unsupported operand type(s) for +: 'frozenset' and 'list'

- Cause: the operation of fronzeset + list.
- Solution: go to the file that produce the error then change to list(fronzeset) + list.

```shell
make dev.shell.lms
cd /edx/app/edxapp/venvs/edxapp/src/django-wiki/wiki/conf
vi settings.py
```

```shell
make dev.shell.studio
cd /edx/app/edxapp/venvs/edxapp/src/django-wiki/wiki/conf
vi settings.py
```

```python
# before
_default_tag_whitelists = (
    bleach.ALLOWED_TAGS
    + [
        "figure",
        "figcaption",
        "br",
        "hr",
        "p",
        "div",
        "img",
        "pre",
        "span",
        "sup",
        "table",
        "thead",
        "tbody",
        "th",
        "tr",
        "td",
        "dl",
        "dt",
        "dd",
    ]
    + ["h{}".format(n) for n in range(1, 7)]
)

# after
_default_tag_whitelists = list((
    list(bleach.ALLOWED_TAGS)
    + [
        "figure",
        "figcaption",
        "br",
        "hr",
        "p",
        "div",
        "img",
        "pre",
        "span",
        "sup",
        "table",
        "thead",
        "tbody",
        "th",
        "tr",
        "td",
        "dl",
        "dt",
        "dd",
    ]
    + ["h{}".format(n) for n in range(1, 7)]
))
```

```shell
make dev.shell.studio
cd /edx/app/edxapp/venvs/edxapp/lib/python3.8/site-packages/drag_and_drop_v2
vi utils.py
```

```python
# before
ALLOWED_TAGS = bleach.ALLOWED_TAGS + [
    'br',
    'caption',
    'dd',
    'del',
    'div',
    'dl',
    'dt',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'img',
    'p',
    'pre',
    's',
    'strike',
    'span',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'tfoot',
    'th',
    'thead',
    'tr',
    'u',
]

# after
ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'br',
    'caption',
    'dd',
    'del',
    'div',
    'dl',
    'dt',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'img',
    'p',
    'pre',
    's',
    'strike',
    'span',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'tfoot',
    'th',
    'thead',
    'tr',
    'u',
]
```
