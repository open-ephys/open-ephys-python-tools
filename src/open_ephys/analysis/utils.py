import re


def alphanum_key(s):
    """
    Turn a string into a list of string and number chunks.

    >>> alphanum_key("z23a")
    ["z", 23, "a"]

    """
    return [int(c) if c.isdigit() else c for c in re.split("([0-9]+)", s)]
