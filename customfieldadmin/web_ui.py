# -*- coding: utf-8 -*-

from genshi.core import START, END
from genshi.filters.transform import Transformer

from trac.core import Component, implements
from trac.web.api import IRequestFilter, ITemplateStreamFilter

from customfieldadmin.api import CustomFields


class CustomFieldTypeFilter(Component):

    implements(IRequestFilter, ITemplateStreamFilter)

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if template == 'ticket.html':
            cf_api = CustomFields(self.env)
            cfields = self._get_custom_fields(cf_api)
            ticket = data['ticket']
            context = data['context']
            for field in data.get('fields', ()):
                if field.get('rendered'):
                    continue
                if field.get('skip'):
                    continue
                if 'value' not in field:
                    continue
                name = field['name']
                value = field['value']
                if name not in cfields:
                    continue
                cfield = cfields[name]
                provider = cf_api.get_provider(cfield['type'])
                if not provider:
                    continue
                rendered = provider.render_field(context, cfield, ticket[name])
                if rendered is not None:
                    field['rendered'] = rendered
        return template, data, content_type

    def filter_stream(self, req, method, filename, stream, data):
        if filename == 'ticket.html':
            stream |= self._transformer(data)
        return stream

    def _get_custom_fields(self, cf_api):
        return dict((cfield['name'], cfield)
                    for cfield in cf_api.get_custom_fields())

    def _transformer(self, data):
        cf_api = CustomFields(self.env)
        cfields = self._get_custom_fields(cf_api)
        context = data['context']

        def replace(stream):
            rendered = None

            for kind, data, pos in stream:
                if kind is START:
                    tag, attrs = data
                    id = attrs.get('id')
                    if not id.startswith('field-'):
                        yield kind, data, pos
                        continue
                    name = id[6:]
                    cfield = cfields.get(name)
                    if cfield is None:
                        yield kind, data, pos
                        continue
                    type = cfield['type']
                    provider = cf_api.get_provider(type)
                    if provider is None:
                        yield kind, data, pos
                        continue
                    rendered = provider.render_editor(context, cfield,
                                                      attrs.get('value'))
                    if not rendered:
                        yield kind, data, pos
                elif kind is END:
                    if rendered:
                        for event in rendered:
                            yield event
                        rendered = None
                    else:
                        yield kind, data, pos
                elif not rendered:
                    yield kind, data, pos

        t = Transformer('//fieldset[@id="properties"]//input[@type="text"]')
        return t.filter(replace)
