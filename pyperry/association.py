import re
import pyperry.base
from pyperry import errors
from pyperry.relation import Relation

class Association(object):
    """
    Associations allow you to retrieve a model or collection of models that are
    related to one another in some way. Here we are concerned with how
    associations are defined and implemented. For documentation on how to use
    associations in your models, please see the belongs_to, has_one, and
    has_many methods on pyperry.Base.

    To understand how associations work, we must define the concepts of a
    source class and a target class for an association.

    target class - the class on which you define the association
    source class - the class of the records returned by calling the association
                   method on the target class

    An example showing the difference between source and target classes::

        class Car(pyperry.Base): pass
        class Part(pyperry.Base): pass

        # Car is the target class and Part is the source class
        Car.has_many('parts', class_name='Part')

        # Part is the target class and Car is the source class
        Part.belongs_to('car', class_name='Car')

        c = Car.first()
        # returns a collection of Part instances (Part is the source class)
        c.parts()

        p = Part().first()
        # returns an instance of Car (Car is the source class)
        p.car()

    Now let's look at what happens when you define an association on a model.
    We will use the association Car.has_many('parts', class_name='Part') as an
    example because all associations work in the same general way. In this
    example, a HasMany class (an Association subclass) is instantiated where
    Car is given as the target_klass argument, and 'parts' is given as the id
    argument. Because we passed in 'Part' for the class_name option, it is used
    as the source class for this association.

    The association id is used to name association method that gets defined on
    the target class. So in our example, all Car instances now have a parts()
    method they can call to retrieve a collection of parts for that car. When
    you call the association method on the target class, a relation (or scope)
    is constructed for the source class representing all of the records related
    to the target class. For associations that represent collections, such as
    has_many, a relation is returned that you can further modify. For
    associations that represent a single object, such as belongs_to or has_one,
    an instance of that model is returned.

    In summarry, all associations do is create scopes on source classes that
    represent records from the source class that are related to (or associated
    with) a target class. Then this scope is packaged as a convenient, easy to
    use, easy to remember method on the target class.

    This means that calling car.parts() is just returning a scope like::

        Part.scoped().where({'car_id': car.id})

    Similarly, calling part.car() is just returning a scope like::

        Car.scoped().where({'id': part.car_id}).first()

    """

    def __init__(self, target_klass, id, **kwargs):
        self.target_klass = target_klass
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

    def primary_key(self, target_instance=None):
        pk_option = self.options.get('primary_key')
        if pk_option is not None:
            primary_key = pk_option
        elif isinstance(self, BelongsTo):
            primary_key = self.source_klass(target_instance).primary_key()
        else:
            primary_key = self.target_klass.primary_key()

        return primary_key

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


    def source_klass(self, obj=None):
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
        class_name = self.target_klass.resolve_name(string)
        if not class_name:
            raise errors.ModelNotDefined, 'Model %s is not defined.' % (string)
        elif len(class_name) > 1:
            raise errors.AmbiguousClassName, ('Class name %s is'
                ' ambiguous.  Use the namespace option to get your'
                ' specific class.  Got classes %s' % (string, str(class_name)))
        return class_name[0]

    def _base_scope(self, obj):
        return self.source_klass(obj).scoped().apply_finder_options(
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

    def scope(self, obj):
        """
        Returns a scope on the source class containing this association

        Builds conditions on top of the base_scope generated from any finder
        options set with the association::

            belongs_to('foo', foreign_key='foo_id')

        In addition to any finder options included with the association options
        the following scope will be added::

            where('id = %s' % target['foo_id'])

        """
        if hasattr(obj, self.foreign_key) and obj[self.foreign_key]:
            return self._base_scope(obj).where({
                self.primary_key(): obj[self.foreign_key]
            })

class Has(Association):

    # Foreign key attributes
    def get_foreign_key(self):
        if super(Has, self).foreign_key:
            return super(Has, self).foreign_key
        elif self.polymorphic():
            return '%s_id' % self.options['_as']
        else:
            return '%s_id' % self.target_klass.__name__.lower()

    def set_foreign_key(self, value):
        self.options['foreign_key'] = value
    foreign_key = property(get_foreign_key, set_foreign_key)

    def polymorphic(self):
        return self.options.has_key('_as')

    def polymorphic_type(self):
        return '%s_type' % self.options['_as']

    def scope(self, obj):
        """
        Returns a scope on the source class containing this association

        Builds conditions on top of the base_scope generated from any finder
        options set with the association::

            has_many('widgets', klass=Widget, foreign_key='widget_id')
            has_many('comments', _as='parent')

        In addition to any finder options included with the association options
        the following will be added::

            where('widget_id = %s ' % target['id'])

        Or for the polymorphic :comments association::

            where('parent_id = %s AND parent_type = %s' % (target['id'],
            target.class))

        """
        pk_attr = self.primary_key()
        if hasattr(obj, pk_attr) and obj[pk_attr]:
            scope = self._base_scope(obj).where({
                self.foreign_key: obj[pk_attr]
            })
            if self.polymorphic():
                scope = scope.where({
                    self.polymorphic_type(): obj.__class__.__name__
                })
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

class HasManyThrough(Has):

    def type(self):
        return 'has_many_through'

    def collection(self):
        return True

    def polymorphic(self):
        return False

    def proxy_association(self):
        if not hasattr(self, '_proxy_association'):
            through = self.options.get('through')
            proxy = self.target_klass.defined_associations.get(through)
            if not proxy: raise errors.AssociationNotFound(
                    "has_many_through: '%s' is not an association on %s" % (
                    str(through), str(self.target_klass)))
            self._proxy_association = proxy
        return self._proxy_association

    def source_association(self):
        if not hasattr(self, '_source_association'):
            source = self.proxy_association().source_klass()
            source_option = self.options.get('source')
            association = (source.defined_associations.get(self.id) or
                           source.defined_associations.get(source_option))
            if not association: raise errors.AssociationNotFound(
                    "has_many_through: '%s' is not an association on %s" % (
                    str(source_option or self.id), str(source)))
            self._source_association = association
        return self._source_association

    def source_klass(self):
        source_type = self.options.get('source_type')
        return self.source_association().source_klass(source_type)

    def scope(self, obj):
        source = self.source_association()
        proxy = self.proxy_association()
        key_attr = (source.foreign_key if source.type() == 'belongs_to' else
                    proxy.primary_key()) # TODO: hmm... source or proxy?

        proxy_ids = (lambda: [getattr(x, key_attr) for x in proxy.scope(obj)])

        relation = self.source_klass().scoped()
        if source.type() == 'belongs_to':
            source_type_option = self.options.get('source_type')
            relation = relation.where(lambda: {
                source.primary_key(source_type_option): proxy_ids()
            })
        else:
            relation = relation.where(lambda: {
                source.foreign_key: proxy_ids()
            })
            if source.polymorphic():
                proxy_source = proxy.source_klass(obj)
                poly_type_attr = source.polymorphic_type()
                poly_type_name = proxy_source.__name__
                relation = relation.where({ poly_type_attr: poly_type_name })

        return relation
