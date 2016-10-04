# (C) British Crown Copyright 2016, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

# import iris tests first so that some things can be initialised before importing anything else
import iris.tests as tests

import codecs
from collections import deque
import json
import os
from Queue import Queue
import requests
from threading import Thread

# maximum number of threads for multi-threading code
MAXTHREADS = 128

class _ResolveWorkerThread(Thread):
    """
    A :class:threading.Thread which moves objects from an input queue to an
    output deque using a 'dowork' method, as defined by a subclass.
    """
    def __init__(self, aqueue, adeque):
        self.queue = aqueue
        self.deque = adeque
        Thread.__init__(self)
        self.daemon = True

    def run(self):
        while not self.queue.empty():
            resource = self.queue.get()
            result = requests.get(resource)
            if (result.status_code == 200 and
                resource.startswith('https://scitools.github.io')):
                self.deque.append(resource)

            self.queue.task_done()


class TestImageFile(tests.IrisTest):
    def test_resolve(self):
        repo_fname = os.path.join(os.path.dirname(__file__), 'results',
                                  'imagerepo.json')
        with open(repo_fname, 'rb') as fi:
            repo = json.load(codecs.getreader('utf-8')(fi))
        uris = []
        for k, v in repo.iteritems():
            uris = uris + v
        uri_list = deque()
        uri_queue = Queue()
        uri_queue_length = len(uris)
        for uri in uris:
            uri_queue.put(uri)

        for i in range(MAXTHREADS):
            _ResolveWorkerThread(uri_queue, uri_list).start()
        uri_queue.join()
        self.assertEqual(len(uri_list), uri_queue_length)

if __name__ == "__main__":
    tests.main()
