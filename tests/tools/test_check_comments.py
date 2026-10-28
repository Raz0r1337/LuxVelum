import unittest
from pathlib import Path

import check_comments as cc

NOTICE = "# Lamp rules ported from Everwood (https://example.org/everwood),\n# Copyright (c) 2026 Sam, MIT licence\n"
CODE = "import math\n\nVALUE = math.pi\n"


def flagged(source):
    return [line for line, _ in cc.python_comments(source)]


class PythonNotices(unittest.TestCase):
    def test_a_notice_block_at_the_top_is_accepted(self):
        self.assertEqual(flagged(NOTICE + CODE), [])
        self.assertEqual(flagged("\n\n" + NOTICE + CODE), [])
        self.assertEqual(flagged("#!/usr/bin/env python3\n" + NOTICE + CODE), [])
        self.assertEqual(flagged("# SPDX-License-Identifier: MIT\n" + CODE), [])

    def test_a_top_block_without_a_notice_is_rejected(self):
        self.assertEqual(flagged("# Lamp rules\n# read the lights\n" + CODE), [1, 2])

    def test_comments_outside_the_notice_block_are_rejected(self):
        self.assertEqual(flagged(NOTICE + "\n# a remark\n" + CODE), [4])
        self.assertEqual(flagged(NOTICE + CODE + "# Copyright (c) 2026 Sam\n"), [6])
        self.assertEqual(flagged(CODE + NOTICE), [4, 5])
        self.assertEqual(flagged(NOTICE + "VALUE = 1  # the value\n"), [3])

    def test_docstrings_stay_rejected_below_a_notice(self):
        self.assertEqual(flagged(NOTICE + '"""Module."""\n' + CODE), [3])

    def test_tool_directives_stay_accepted(self):
        self.assertEqual(flagged(CODE + "VALUE = 1  # noqa: E501\n"), [])


class OtherLanguages(unittest.TestCase):
    def test_c_like_and_cmake_rules_are_unchanged(self):
        self.assertEqual([line for line, _ in cc.c_like_comments("// Copyright (c) 2026\n// a remark\nint x;\n")],
                         [2])
        self.assertEqual([line for line, _ in cc.cmake_comments("# Copyright (c) 2026\nset(X 1)\n")], [1])


class RepositorySources(unittest.TestCase):
    def test_the_lamp_rules_notice_passes(self):
        source = (Path(cc.ROOT) / "tools" / "lamp_rules.py").read_text(encoding="utf-8")
        self.assertEqual(list(cc.python_comments(source)), [])
        self.assertTrue(cc.LEGAL_NOTICE.search(source.splitlines()[1]))


if __name__ == "__main__":
    unittest.main()
