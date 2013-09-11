# -*- coding: utf-8 -*-
import json
import unittest
from pysolarized.solr import Solr


class TestInstrumentation(unittest.TestCase):

    def testUrlJoin(self):
        from solr import _get_url
        url = _get_url("http://example.com", "/update/")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("http://example.com/", "/update")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("http://example.com", "update")
        self.assertEquals(url, "http://example.com/update")
        url = _get_url("127.0.0.1", "something/something/darkside")
        self.assertEquals(url, "127.0.0.1/something/something/darkside")


class TestSolrUpdates(unittest.TestCase):

    def setUp(self):
        self._clear_handler()

    def _command_handler(self, url, command):
        self.req_urls.append(url)
        self.req_commands.append(command)

    def _clear_handler(self):
        self.req_urls = []
        self.req_commands = []

    def testSolrInterface(self):
        # Check configuration with string only
        url = "http://this.is.a.mock.url"
        solr = Solr(url)
        solr._send_solr_command = self._command_handler
        solr.commit()
        self.assertEquals(self.req_urls[0], url)

    def testUpdateDispatch(self):
        url = "http://this.is.a.failure.fail"
        document1 = {u"name": u"Joe", u"surname": u"Satriani", u"booboo": 12}
        document2 = {u"name": u"Joanna", u"surname": u"S šuuumnikiiiič!", u"booboo": 12}

        solr = Solr({"en": url}, "en")
        solr._send_solr_command = self._command_handler
        solr.add([document1])
        solr.commit()

        self.assertEquals(self.req_urls[0], url)
        self.assertEquals(self.req_urls[1], url)
        self.assertEqual({"add": {"doc": document1}}, json.loads(self.req_commands[0]))
        self.assertEqual({"commit": {}}, json.loads(self.req_commands[1]))

        self._clear_handler()
        solr.add([document1, document2])
        solr.commit()

        self.assertEquals(self.req_urls[0], url)
        self.assertEquals(self.req_urls[1], url)

        self.assertEquals(self.req_commands[0], u"{\"add\":{\"doc\": %s},\"add\":{\"doc\": %s}}" % (json.dumps(document1),
                                                                                                    json.dumps(document2)))
        self.assertEqual({"commit": {}}, json.loads(self.req_commands[1]))

    def testUpdateDocBoost(self):
        url = "http://this.is.a.mock.url"
        document1 = {u"name": u"Joe", u"surname": u"Satriani", u"booboo": 12}

        solr = Solr({"en": url}, "en")
        solr._send_solr_command = self._command_handler
        solr.add(document1, boost=10.0)
        solr.commit()
        self.assertEquals(self.req_urls[0], url)
        self.assertEquals(self.req_urls[1], url)
        self.assertEqual({"add": {"doc": document1, "boost": 10.0}}, json.loads(self.req_commands[0]))
        self.assertEqual({"commit": {}}, json.loads(self.req_commands[1]))

    def testAddFlushBatch(self):
        url = "http://this.is.a.mock.url"
        document1 = {u"name": u"Joe", u"surname": u"Satriani", u"booboo": 12}
        document2 = {u"name": u"Joanna", u"surname": u"S šuuumnikiiiič!", u"booboo": 10}
        document3 = {u"name": u"Lester", u"surname": u"Burnham", u"booboo": 7}

        import pysolarized.solr
        oldaddbatch = pysolarized.solr.SOLR_ADD_BATCH
        pysolarized.solr.SOLR_ADD_BATCH = 1
        solr = Solr({"en": url}, "en")
        solr._send_solr_command = self._command_handler

        solr.add(document1)
        solr.add(document2)
        solr.add(document3)
        solr.commit()

        self.assertEqual('{"add":{"doc": {"surname": "Satriani", "name": "Joe", "booboo": 12}},"add":{"doc": {"surname": "S \\u0161uuumnikiiii\\u010d!", "name": "Joanna", "booboo": 10}}}', self.req_commands[0])
        self.assertEqual({'add': {'doc': document3}}, json.loads(self.req_commands[1]))
        self.assertEqual({"commit": {}}, json.loads(self.req_commands[2]))

        pysolarized.solr.SOLR_ADD_BATCH = oldaddbatch


class testSolrQueries(unittest.TestCase):

    query_response = """
        { "responseHeader": { "status":0, "QTime" : 45 },
          "response" : { "numFound" : 1, "start": 31,
                         "docs" : [ {"title" : "This is woot", "content" : "This isn't woot." } ]},
          "facet_counts": { "facet_fields" : { "source" : { "newspaper" : 342 }}, "facet_dates":{},"facet_queries":{}, "facet_ranges":{}},
          "highlighting": { "ididid" : { "content": [ "... blah blah ..."]}}}
    """

    def _query_handler(self, url, command):
        self.query_url = url
        self.query_params = command
        return json.loads(self.query_response)

    def setUp(self):
        self.query_url = None
        self.query_params = None

    def testQueryDispatch(self):
        url = "http://this.is.a.failure.fail"
        solr = Solr({"en": url}, "en")
        solr._send_solr_query = self._query_handler

        query = u"what is a treeš"
        filters = {"meaning": "deep"}
        sort = ["deepness", "wideness"]
        columns = ["title", "content"]
        start = 31
        rows = 84

        results = solr.query(query,
                             filters=filters,
                             columns=columns,
                             sort=sort,
                             start=start,
                             rows=rows)

        self.assertEquals(self.query_url, "%s/select" % (url,))
        expected = { 'q': query,
                     'json.nl': 'map',
                     'fl': ",".join(columns),
                     'start': str(start),
                     'rows': str(rows),
                     'fq': '%s:%s' % (filters.keys()[0], filters.values()[0]),
                     'wt': 'json',
                     'sort': ",".join(sort)}

        self.assertEqual(self.query_params, expected)
        self.assertTrue(results is not None)

        # Check results
        self.assertEquals(results.results_count, 1)
        self.assertEquals(results.query_time, 45)
        self.assertEqual(results.documents[0], {"title": "This is woot", "content": "This isn't woot."})
        self.assertEqual(results.facets, {"source": [("newspaper", 342)]})
        self.assertEqual(results.highlights, {'ididid': {"content": ["... blah blah ..."]}})

class testMultipleCores(unittest.TestCase):
    def setUp(self):
        self._clear_handler()

    def _command_handler(self, url, command):
        self.req_urls.append(url)
        self.req_commands.append(command)

    def _clear_handler(self):
        self.req_urls = []
        self.req_commands = []

    def testSolrHandlers(self):
        document1 = {u"name": u"Joe", u"surname": u"Satriani", u"booboo": 12}
        document2 = {u"name": u"Joanna", u"surname": u"S šuuumnikiiiič!", u"booboo": 12}

        solr = Solr('http://example/solr/core1/')
        solr._send_solr_command = self._command_handler
        solr.add([document1])
        solr.commit()

        solr = Solr('http://example/solr/core2/')
        solr._send_solr_command = self._command_handler
        self.assertEquals(len(solr._add_batch), 0)

        solr.add([document2])
        solr.commit()

if __name__ == "__main__":
    unittest.main()
