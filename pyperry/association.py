import re
import pyperry.base
from pyperry import errors
from pyperry.relation import Relation

class Association(object):

    def __init__(self, source_klass, id, **kwargs):
        self.source_klass = source_klass
        self.id = id
        self.options = kwargs

    def __call__(self, obj):
        if self.collection():
            return self.scope(obj)
        return self.scope(obj).first()

    def type(self):
        raise NotImplementedError, 'You must define the type in subclasses.'

    def polymorphic(self):
        raise NotImplementedError, ('You must define how your association is'
            'polymorphic in subclasses.')

    def collection(self):
        raise NotImplementedError, 'You must define collection in subclasses.'

    def scope(self):
        raise NotImplementedError, 'You must define scope in subclasses.'

    # Primary key attributes
    # There is a better way to do the property as a decorator, but it does not
    # => work in Python2.5
    def get_primary_key(self):
        return self.options.get('primary_key') or 'id'

    def set_primary_key(self, value):
        self.options['primary_key'] = value
    primary_key = property(get_primary_key, set_primary_key)

    # Foreign key attributes
    def get_foreign_key(self):
        return self.options.get('foreign_key')

    def set_foreign_key(self, value):
        self.options['foreign_key'] = value
    foreign_key = property(get_foreign_key, set_foreign_key)

    def eager_loadable(self):
        for option in self.finder_options():
            if type(self.options.get(option)).__name__ == 'function':
                return False
        return True

    # MBM: This needs to be moved somewhere else. Probably in a constant.
    def finder_options(self):
        return (Relation.singular_query_methods + Relation.plural_query_methods +
            Relation.aliases.keys())


    def target_klass(self, obj=None):
        poly_type = None
        if (self.options.has_key('polymorphic') and
            self.options['polymorphic'] and obj):
            if type(obj.__class__) in [pyperry.base.Base, pyperry.base.BaseMeta]:
                poly_type = getattr(obj, '%s_type' % self.id)
            else:
                poly_type = obj

        if poly_type:
            type_list = [
                self.options.get('namespace'),
                self._sanitize_type_attribute(poly_type)
            ]
            type_string = '.'.join([arg for arg in type_list if arg])
            return self._get_resolved_class(type_string)
        else:
            if not self.options.get('klass') and not self.options.get('class_name'):
                raise errors.ArgumentError, ('klass or class_name option'
                    ' required for association declaration.')
            if self.options.get('klass'):
                if type(self.options.get('klass')).__name__ == 'function':
                    return self.options.get('klass')()
                return self.options.get('klass')
            elif self.options.get('class_name'):
                type_list = [
                    self.options.get('namespace'),
                    self.options['class_name']
                ]
                type_string = '.'.join([arg for arg in type_list if arg])
                return self._get_resolved_class(type_string)

    def _get_resolved_class(self, string):
        class_name = self.source_klass.resolve_name(string)
        if not class_name:
            raise errors.ModelNotDefined, 'Model %s is not defined.' % (string)
        elif len(class_name) > 1:
            raise errors.AmbiguousClassName, ('Class name %s is'
                ' ambiguous.  Use the namespace option to get your'
                ' specific class.  Got classes %s' % (string, str(class_name)))
        return class_name[0]

    def _base_scope(self, obj):
        return self.target_klass(obj).scoped().apply_finder_options(
            self._base_finder_options(obj))

    def _base_finder_options(self, obj):
        opts = {}
        for option in self.finder_options():
            value = self.options.get(option)
            if value:
                if type(self.options[option]).__name__ == 'function':
                    opts[option] = value()
                else:
                    opts[option] = value
        return opts

    def _sanitize_type_attribute(self, string):
        return re.sub('[^a-zA-z]\w*', '', string)

class BelongsTo(Association):

    def type(self):
        return 'belongs_to'

    def collection(self):
        return False

    # Foreign key attributes
    def get_foreign_key(self):
        return super(BelongsTo, self).foreign_key or '%s_id' % self.id

    def set_foreign_key(self, value):
        self.options['foreign_key'] = value
    foreign_key = property(get_foreign_key, set_foreign_key)

    def polymorphic(self):
        return self.options.has_key('polymorphic') and self.options['polymorphic']

    def polymorphic_type(self):
        return '%s_type' % self.id

    ##
    # Returns a scope on the target containing this association
    #
    # Builds conditions on top of the base_scope generated from any finder
    # options set with the association
    #
    # belongs_to('foo', foreign_key='foo_id')
    #
    # In addition to any finder options included with the association options
    # the following scope will be added:
    #  where('id = %s' % source['foo_id'])
    #
    def scope(self, obj):
        if hasattr(obj, self.foreign_key) and obj[self.foreign_key]:
            return self._base_scope(obj).where({ self.primary_key:
                obj[self.foreign_key] })

class Has(Association):

    # Foreign key attributes
    def get_foreign_key(self):
        if super(Has, self).foreign_key:
            return super(Has, self).foreign_key
        elif self.polymorphic():
            return '%s_id' % self.options['_as']
        else:
            return '%s_id' % self.source_klass.__name__.lower()

    def set_foreign_key(self, value):
        self.options['foreign_key'] = value
    foreign_key = property(get_foreign_key, set_foreign_key)

    def polymorphic(self):
        return self.options.has_key('_as')

    def polymorphic_type(self):
        return '%s_type' % self.options['_as']

    ##
    # Returns a scope on the target containing this association
    #
    # Builds conditions on top of the base_scope generated from any finder
    # options set with the association
    #
    #   has_many('widgets', klass=Widget, foreign_key='widget_id')
    #   has_many('comments', _as='parent')
    #
    # In addition to any finder options included with the association options
    # the following will be added:
    #
    #   where('widget_id = %s ' % source['id'])
    #
    # Or for the polymorphic :comments association:
    #
    #   where('parent_id = %s AND parent_type = %s' % (source['id'], source.class))
    #
    def scope(self, obj):
        if hasattr(obj, self.primary_key) and obj[self.primary_key]:
            scope = self._base_scope(obj).where({ self.foreign_key:
                obj[self.primary_key] })
            if self.polymorphic():
                scope = scope.where({ self.polymorphic_type():
                    obj.__class__.__name__ })
            return scope

class HasMany(Has):

    def type(self):
        return 'has_many'

    def collection(self):
        return True

class HasOne(Has):

    def type(self):
        return 'has_one'

    def collection(self):
        return False


