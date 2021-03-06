# -*- coding: utf-8 -*-
"""
API for administrating custom ticket fields in Trac.
Supports creating, getting, updating and deleting custom fields.

License: BSD

(c) 2005-2012 ::: www.CodeResort.com - BV Network AS (simon-code@bvnetwork.no)
"""

import re

from pkg_resources import resource_filename

from trac.core import Component, ExtensionPoint, Interface, TracError, \
                      implements
from trac.ticket.api import TicketSystem

try:
    from  trac.util.translation import domain_functions
    add_domain, _, tag_ = \
        domain_functions('customfieldadmin', ('add_domain', '_', 'tag_'))
except:
    # fall back to 0.11 behavior, i18n functions are no-ops then
    from genshi.builder import tag as tag_
    from trac.util.translation import gettext as _
    def add_domain(*args, **kwargs):
        pass


__all__ = ['CustomFields', 'ICustomFieldTypeProvider']


class ICustomFieldTypeProvider(Interface):

    def get_supported_types():
        """Return a list of extra type and localized label of custom field.

        Each item must be `(name, label)` tuple.
        """

    def get_property_names(type):
        """Return a list of property names for `type`.

        The property names will be used for `<name>.<property> = ...` in
        [ticket-custom] section.
        """

    def render_field(context, cfield, value):
        """Return a Fragment object of Genshi for field in ticket view.

        If `None` is returned, `value` will be shown without changes.
        """

    def render_editor(context, cfield, value):
        """Return a Fragment object of Genshi for `type` field in ticket form.
        """

    def render_admin_field(context, type, cfield={}):
        """Iterate Fragment objects of Genshi for `type` field in custom
        field admin panel.
        """

    def validate_admin_field(cfield):
        """Validate a custom field in admin panel.

        Iterate `(name, message)` tuples for problems detected in the
        `cfield`.
        """


class CustomFields(Component):
    """ These methods should be part of TicketSystem API/Data Model.
    Adds update_custom_field and delete_custom_field methods.
    (The get_custom_fields is already part of the API - just redirect here,
     and add option to only get one named field back.)

    Input to methods is a 'cfield' dict supporting these keys:
        name = name of field (ascii alphanumeric only)
        type = text|checkbox|select|radio|textarea
        label = label description
        value = default value for field content
        options = options for select and radio types
                  (list, leave first empty for optional)
        cols = number of columns for text area
        rows = number of rows for text area
        order = specify sort order for field
        format = text|wiki (for text and textarea)
    """

    implements()

    providers = ExtensionPoint(ICustomFieldTypeProvider)

    config_options = ['label', 'value', 'options', 'cols', 'rows',
                         'order', 'format']

    std_types = ('text', 'select', 'checkbox', 'radio', 'textarea')

    def __init__(self):
        # bind the 'customfieldadmin' catalog to the specified locale directory
        try:
            locale_dir = resource_filename(__name__, 'locale')
            add_domain(self.env.path, locale_dir)
        except KeyError:
            # No 'locale', hence no compiled message catalogs. Ignore.
            pass
        # TODO: Remove systeminfo compat code when only supporting Trac>=0.12
        try:
            from trac.loader import get_plugin_info
        except ImportError:
            from customfieldadmin import __version__
            self.env.systeminfo.append(('CustomFieldAdmin', __version__))

    def get_custom_fields(self, cfield=None):
        """ Returns the custom fields from TicketSystem component.
        Use a cfdict with 'name' key set to find a specific custom field only.
        """
        items = TicketSystem(self.env).get_custom_fields()
        for item in items:
            if item['type'] == 'textarea':
                item['cols'] = item.pop('width')
                item['rows'] = item.pop('height')
            elif item['type'] == 'text':
                config_get = self.config.get
                type = config_get('ticket-custom', item['name'] + '.type')
                provider = self.get_provider(type)
                if provider:
                    item['type'] = type
                    for prop in provider.get_property_names(type):
                        item[prop] = config_get('ticket-custom',
                                                item['name'] + '.' + prop)
            if cfield and item['name'] == cfield['name']:
                return item  # only return specific item with cfname
        if cfield:
            return None   # item not found
        else:
            return items  # return full list

    def verify_custom_field(self, cfield, create=True):
        """ Basic validation of the input for modifying or creating
        custom fields. """
        # Requires 'name' and 'type'
        if not (cfield.get('name') and cfield.get('type')):
            raise TracError(
                    _("Custom field requires attributes 'name' and 'type'."))
        # Use lowercase custom fieldnames only
        cfield['name'] = cfield['name'].lower()
        # Only alphanumeric characters (and [-_]) allowed for custom fieldname
        if re.search('^[a-z][a-z0-9_]+$', cfield['name']) == None:
            raise TracError(_("Only alphanumeric characters allowed for " \
                             "custom field name ('a-z' or '0-9' or '_'), " \
                             "with 'a-z' as first character."))
        # Name must begin with a character - anything else not supported by Trac
        if not cfield['name'][0].isalpha():
            raise TracError(
                    _("Custom field name must begin with a character (a-z)."))
        # Check that it is a valid field type
        provider = None
        if not cfield['type'] in self.std_types:
            provider = self.get_provider(cfield['type'])
            if not provider:
                raise TracError(_("%(field_type)s is not a valid field type",
                                  field_type=cfield['type']))
            for prop, message in provider.validate_admin_field(cfield):
                raise TracError("%(name)s.%(prop)s: %(message)s" %
                                dict(name=cfield['name'], prop=prop,
                                     message=message))
        # Check that field does not already exist
        # (if modify it should already be deleted)
        if create and self.config.get('ticket-custom', cfield['name']):
            raise TracError(_("Can not create as field already exists."))

    def create_custom_field(self, cfield):
        """ Create the new custom fields (that may just have been deleted as
        part of 'modify'). In `cfield`, 'name' and 'type' keys are required.
        Note: Caller is responsible for verifying input before create."""
        # Need count pre-create for correct order
        count_current_fields = len(self.get_custom_fields())
        # Set the mandatory items
        type = cfield['type']
        if type in self.std_types:
            provider = None
            self.config.set('ticket-custom', cfield['name'], type)
        else:
            provider = self.get_provider(cfield['type'])
            self.config.set('ticket-custom', cfield['name'], 'text')
            self.config.set('ticket-custom', cfield['name'] + '.type', type)
            for prop in provider.get_property_names(type):
                self.config.set('ticket-custom', cfield['name'] + '.' + prop,
                                cfield.get(prop))
        # Label = capitalize fieldname if not present
        self.config.set('ticket-custom', cfield['name'] + '.label',
                        cfield.get('label') or cfield['name'].capitalize())
        # Optional items
        if 'value' in cfield:
            self.config.set('ticket-custom', cfield['name'] + '.value',
                                                        cfield['value'])
        if 'options' in cfield:
            if cfield.get('optional', False):
                self.config.set('ticket-custom', cfield['name'] + '.options',
                                '|' + '|'.join(cfield['options']))
            else:
                self.config.set('ticket-custom', cfield['name'] + '.options',
                               '|'.join(cfield['options']))
        if 'format' in cfield and cfield['type'] in ('text', 'textarea'):
            self.config.set('ticket-custom', cfield['name'] + '.format',
                                                        cfield['format'])
        # Textarea
        if cfield['type'] == 'textarea':
            cols = cfield.get('cols') and int(cfield.get('cols', 0)) > 0 \
                                                and cfield.get('cols') or 60
            rows = cfield.get('rows', 0) and int(cfield.get('rows', 0)) > 0 \
                                                and cfield.get('rows') or 5
            self.config.set('ticket-custom', cfield['name'] + '.cols', cols)
            self.config.set('ticket-custom', cfield['name'] + '.rows', rows)
        # Order
        order = cfield.get('order') or count_current_fields + 1
        self.config.set('ticket-custom', cfield['name'] + '.order', order)
        self._save(cfield)

    def update_custom_field(self, cfield, create=False):
        """ Updates a custom field. Option to 'create' is kept in order to keep
        the API backwards compatible. """
        if create:
            self.verify_custom_field(cfield)
            self.create_custom_field(cfield)
            return
        # Check input, then delete and save new
        if not self.get_custom_fields(cfield=cfield):
            raise TracError(_("Custom Field '%(name)s' does not exist. " \
                    "Cannot update.", name=cfield.get('name') or '(none)'))
        self.verify_custom_field(cfield, create=False)
        self.delete_custom_field(cfield, modify=True)
        self.create_custom_field(cfield)

    def delete_custom_field(self, cfield, modify=False):
        """ Deletes a custom field. Input is a dictionary
        (see update_custom_field), but only ['name'] is required.
        """
        if not self.config.get('ticket-custom', cfield['name']):
            return # Nothing to do here - cannot find field
        if not modify:
            # Permanent delete - reorder later fields to lower order
            order_to_delete = self.config.getint('ticket-custom',
                                                    cfield['name']+'.order')
            cfs = self.get_custom_fields()
            for field in cfs:
                if field['order'] > order_to_delete:
                    self.config.set('ticket-custom', field['name']+'.order',
                                                    field['order'] -1 )
        supported_options = [cfield['name']] + \
            [cfield['name']+'.'+opt for opt in self.config_options]
        for option, _value in self.config.options('ticket-custom'):
            if modify and not option in supported_options:
                # Only delete supported options when modifying
                # http://trac-hacks.org/ticket/8188
                continue
            if option == cfield['name'] \
                    or option.startswith(cfield['name'] + '.'):
                self.config.remove('ticket-custom', option)
        # Persist permanent deletes
        if not modify:
            self._save(cfield)

    def get_provider(self, name):
        for provider in self.providers:
            for name_, label in provider.get_supported_types():
                if name == name_:
                    return provider

    def _save(self, cfield=None):
        """ Saves a value, clear caches if needed / supported. """
        self.config.save()
        try:
            # cache support for Trac >= 0.12
            del TicketSystem(self.env).custom_fields
        except AttributeError:
            # 0.11 cached values internally
            TicketSystem(self.env)._custom_fields = None
        # Re-populate contents of cfield with new values and defaults
        if cfield:
            stored = self.get_custom_fields(cfield=cfield)
            if stored: # created or updated (None for deleted so just ignore)
                cfield.update(stored)
