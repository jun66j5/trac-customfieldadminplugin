# -*- coding: utf-8 -*-
"""
License: BSD

(c) 2005-2012 ::: www.CodeResort.com - BV Network AS (simon-code@bvnetwork.no)
"""

import unittest

from trac.core import TracError
from trac.test import EnvironmentStub, Mock

from customfieldadmin.api import CustomFields

class CustomFieldApiTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        self.cf_api = CustomFields(self.env)

    def tearDown(self):
        if hasattr(self.env, 'destroy_db'):
            self.env.destroy_db()
        del self.env

    def test_systeminfo(self):
        try:
            from trac.loader import get_plugin_info
            # From ~0.12, Trac handles plugins and versions - no need to test
            return
        except ImportError:
            self.assertTrue(('CustomFieldAdmin',
                __import__('customfieldadmin', ['__version__']).__version__) \
                    in self.env.systeminfo)

    def test_create(self):
        for f in ['one', 'two', 'three']:
            cfield = {'name': f, 'type': 'text'}
            self.cf_api.create_custom_field(cfield)
        self.assertEquals(self.cf_api.get_custom_fields(),
                    [{'name': u'one', 'format': 'plain', 'value': '',
                      'label': u'One', 'type': u'text', 'order': 1},
                     {'name': u'two', 'format': 'plain', 'value': '',
                      'label': u'Two', 'type': u'text', 'order': 2},
                     {'name': u'three', 'format': 'plain', 'value': '',
                      'label': u'Three', 'type': u'text', 'order': 3}])

    def test_update(self):
        cfield = {'name': 'foo', 'type': 'text'}
        self.cf_api.create_custom_field(cfield)
        self.assertEquals(cfield, {'name': u'foo', 'format': 'plain',
                'value': '', 'label': u'Foo', 'type': u'text', 'order': 1})
        cfield['label'] = 'Answer'
        cfield['value'] = '42'
        self.cf_api.update_custom_field(cfield=cfield)
        self.assertEquals(cfield, {'name': u'foo', 'format': 'plain',
                'value': '42', 'label': u'Answer', 'type': u'text', 'order': 1})

    def test_update_textarea(self):
        cfield = {'name': 'foo', 'type': 'textarea'}
        self.cf_api.create_custom_field(cfield)
        self.assertEquals(cfield, {'name': u'foo', 'format': 'plain',
                                   'value': '', 'label': u'Foo',
                                   'type': u'textarea', 'order': 1,
                                   'cols': 60, 'rows': 5})
        cfield['cols'] = 42
        cfield['rows'] = 3
        self.cf_api.update_custom_field(cfield=cfield)
        self.assertEquals(cfield, {'name': u'foo', 'format': 'plain',
                                   'value': '', 'label': u'Foo',
                                   'type': u'textarea', 'order': 1,
                                   'cols': 42, 'rows': 3})

    def test_update_non_existing(self):
        try:
            self.cf_api.update_custom_field(cfield={'name': 'no_field'})
            self.fail("Huh. Missing exception!")
        except Exception, e:
            self.assertTrue("'no_field'" in e.message)
            self.assertTrue('does not exist' in e.message)

    def test_update_non_existing_no_name(self):
        try:
            self.cf_api.update_custom_field(cfield={})
            self.fail("Huh. Missing exception!")
        except Exception, e:
            self.assertTrue("'(none)'" in e.message)
            self.assertTrue('does not exist' in e.message)

    def test_delete(self):
        for f in ['one', 'two', 'three']:
            cfield = {'name': f, 'type': 'text'}
            self.cf_api.create_custom_field(cfield)
        self.assertEquals(True,
                ('two', 'text') in self.env.config.options('ticket-custom'))
        self.cf_api.delete_custom_field({'name': 'two'})
        self.assertEquals(False,
                ('two', 'text') in self.env.config.options('ticket-custom'))
        #import ipdb; ipdb.set_trace()
        # Note: Should also reorder higher-ordered items
        self.assertEquals(self.cf_api.get_custom_fields(),
                    [{'name': u'one', 'format': 'plain', 'value': '',
                      'label': u'One', 'type': u'text', 'order': 1},
                     {'name': u'three', 'format': 'plain', 'value': '',
                      'label': u'Three', 'type': u'text', 'order': 2}])
        self.assertEquals(None,
                self.cf_api.get_custom_fields(cfield={'name': 'two'}))

    def test_delete_unknown_options(self):
        cf = {'name': 'foo', 'type': 'text', 'label': 'Foo'}
        self.cf_api.create_custom_field(cf)
        self.assertEquals('text',
                    self.env.config.get('ticket-custom', 'foo'))
        self.assertEquals('Foo',
                    self.env.config.get('ticket-custom', 'foo.label'))
        self.env.config.set('ticket-custom', 'foo.answer', '42')
        self.cf_api.delete_custom_field(cf, modify=False)
        self.assertEquals('',
                    self.env.config.get('ticket-custom', 'foo'))
        self.assertEquals('',
                    self.env.config.get('ticket-custom', 'foo.label'))
        self.assertEquals('',
                    self.env.config.get('ticket-custom', 'foo.answer'))

    def test_not_delete_unknown_options_for_modify(self):
        cf = {'name': 'foo', 'type': 'text', 'label': 'Foo'}
        self.cf_api.create_custom_field(cf)
        self.assertEquals('text',
                    self.env.config.get('ticket-custom', 'foo'))
        self.assertEquals('Foo',
                    self.env.config.get('ticket-custom', 'foo.label'))
        self.env.config.set('ticket-custom', 'foo.answer', '42')
        self.cf_api.delete_custom_field(cf, modify=True)
        self.assertEquals('',
                    self.env.config.get('ticket-custom', 'foo'))
        self.assertEquals('',
                    self.env.config.get('ticket-custom', 'foo.label'))
        self.assertEquals('42',
                    self.env.config.get('ticket-custom', 'foo.answer'))

    def test_verify_unknown_type(self):
        self.env.config.set('ticket-custom', 'one', 'foo_type')
        fields = self.cf_api.get_custom_fields()
        self.assertEquals(1, len(fields))
        try:
            self.cf_api.verify_custom_field(fields[0], create=False)
        except TracError, e:
            self.assertTrue("foo_type" in e.message)


class CustomFieldL10NTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        self.cf_api = CustomFields(self.env)

    def tearDown(self):
        if hasattr(self.env, 'destroy_db'):
            self.env.destroy_db()
        del self.env

    def test_translation_function(self):
        from customfieldadmin.api import _
        self.assertEquals('foo bar', _("foo bar"))
        self.assertEquals('foo bar', _("foo %(bar)s", bar='bar'))

    def test_translation_function_tag(self):
        from customfieldadmin.api import tag_
        from genshi.builder import tag
        self.assertEquals('<p>foo bar</p>', str(tag_(tag.p('foo bar'))))
        self.assertEquals('<p>foo bar</p>',
                    str(tag_(tag.p('foo %(bar)s' % {'bar': 'bar'}))))
