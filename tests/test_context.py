#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `m3u8_dl` package."""


import unittest
from click.testing import CliRunner

from m3u8_dl import cli
from m3u8_dl import M3u8Downloader, M3u8Context
import pickle
import tempfile
import os


class TestM3u8Context(unittest.TestCase):
    """Tests for `m3u8_dl` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_context_to_use_like_dict(self):
        self.context = M3u8Context()
        self.context['abc'] = 1
        self.assertEquals(self.context['abc'], 1)

    def test_pickle_dump_and_load_success(self):
        self.context = M3u8Context()
        self.context['file_uri'] = '/folder/file'
        with tempfile.TemporaryDirectory() as tmpdirname:
            path = os.path.join(tmpdirname, '1.pickle')
            with open(path, 'wb') as f:
                pickle.dump(self.context, f)
            with open(path, 'rb') as f:
                new_context = pickle.load(f)
                # self.assertEquals(new_context['file_uri'], '/folder/file')
                for key, value in self.context:
                    new_value = new_context[key]
                    self.assertEquals(value, new_value)
