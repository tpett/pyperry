import re
import pyperry.base
from pyperry import errors
from pyperry.relation import Relation

class Association(object):
    """
    Associations
    ============

    Associations allow you to retrieve a model or collection of models that are
    related to one another in some way. Here we are concerned with how
    associations are defined and implemented. For documentation on how to use
    associations in your models, please see the L{belongs_to
    <pyperry.Base.belongs_to>}, L{has_one <pyperry.Base.has_one>}, and
    L{has_many <pyperry.Base.has_many>} methods on L{pyperry.Base}.

    Terminology
    -----------

    To understand how associations work, we must define the concepts of a
    source class and a target class for an association.

        - B{target class}: the class on which you define the association
        - B{source class}: the class of the records returned by calling the
          association method on the target class

    An example showing the difference between source and target classes::

        class Car(pyperry.Base):
            # Car is the target class and Part is the source class
            parts = HasMany(class_name='Part')

        class Part(pyperry.Base):
            # Part is the target class and Car is the source class
            car = BelongsTo(class_name='Car')

        c = Car.first()
        # returns a collection of Part models (Part is the source class)
        c.parts()

        p = Part.first()
        # returns a Car model (Car is the source class)
        p.car()

    What happens when you define an association
    -------------------------------------------

    Now let's look at what happens when you define an association on a model.
    We will use the association C{Car.has_many('parts', class_name='Part')} as
    an example because all associations work in the same general way. In this
    example, a C{HasMany} class (an C{Association} subclass) is instantiated
    where C{Car} is given as the C{target_klass} argument, and C{'parts'} is
    given as the C{id} argument. Because we passed in C{'Part'} for the
    C{class_name} option, it is used as the source class for this association.

    The association id is used as the name of the association method that gets
    defined on the target class. So in our example, all C{Car} instances now
    have a C{parts()} method that can be called to retrieve a collection of
    parts for a car. When you call the association method on the target class,
    a relation (or scope) is constructed for the source class representing all
    of the records related to the target class. For associations that represent
    collections, such as C{has_many}, a relation is returned that you can
    further modify. For associations that represent a single object, such as
    C{belongs_to} or C{has_one}, an instance of that model is returned.

    In summary, all an association does is create a scope on the source class
    that represents records from the source class that are related to (or
    associated with) the target class. Then a method on the target class is
    created that returns this scope.

    This means that calling C{car.parts()} is just returning a scope like::

        Part.scoped().where({'car_id': car.id})

    Similarly, calling C{part.car()} is just returning a scope like::

        Car.scoped().where({'id': part.car_id}).first()

    """

    def __init__(self, **kwargs):
        self.target_klass = kwargs.get('target_klass')
        self.id = kwargs.get('id')
        self.options = kwargs

    def __call__(self, obj):
        if self.collection():
            return self.scope(obj)
        return self.scope(obj).first()

    def __get__(self, instance, owner):
        """get the relation/instance for this association"""
        if instance is None:
            return self
        elif hasattr(instance, self.cache_id):
            return getattr(instance, self.cache_id)
        else:
            val = self.scope(instance)
            if not self.collection() and val is not None:
                val = val.first()
            setattr(instance, self.cache_id, val)
            return val

    def __set__(self, instance, value):
        """sets the given value to the cache"""
        setattr(instance, self.cache_id, value)

    def __delete__(self, instance):
        """clears the cache attribute"""
        delattr(instance, self.cache_id)

    @property
    def cache_id(self):
        return '_%s_cache' % self.id

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
        return not (self.type() == 'belongs_to' and self.polymorphic())

    # MBM: This needs to be moved somewhere else. Probably in a constant.
    def finder_options(self):
        return (Relation.singular_query_methods + Relation.plural_query_methods +
            Relation.aliases.keys())


    def source_klass(self, obj=None):
        eager_loading = isinstance(obj, list)
        poly_type = None
        if (self.options.has_key('polymorphic') and
            self.options['polymorphic'] and obj):
            if type(obj.__class__) in [pyperry.base.Base, pyperry.base.BaseMeta]:
                poly_type = getattr(obj, '%s_type' % self.id)
            else:
                poly_type = obj

        if eager_loading and not self.eager_loadable():
            raise errors.AssociationPreloadNotSupported(
                    "This association cannot be eager loaded. It either has "
                    "a config with callables, or it is a polymorphic belongs "
                    "to association.")

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
    """
    Builds the association scope for a C{belongs} association. See the
    L{Association} class for more details on how associations work.

    """

    def __set__(self, instance, value):
        super(BelongsTo, self).__set__(instance, value)

        if value is None:
            pk = None
        else:
            pk = value.pk_value()

        setattr(instance, self.get_foreign_key(), pk)

        if self.polymorphic:
            if value is None:
                type_name = None
            else:
                type_name = value.__class__.__name__
            setattr(instance, self.polymorphic_type(), type_name)

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

    def scope(self, obj_or_list):
        """
        Returns a scope on the source class containing this association

        Builds conditions on top of the base_scope generated from any finder
        options set with the association::

            belongs_to('foo', foreign_key='foo_id')

        In addition to any finder options included with the association options
        the following scope will be added::

            where('id = %s' % target['foo_id'])

        """
        if isinstance(obj_or_list, pyperry.Base):
            keys = obj_or_list[self.foreign_key]
        else:
            keys = [o[self.foreign_key] for o in obj_or_list]

        if keys is not None:
            return self._base_scope(obj_or_list).where({
                self.primary_key(obj_or_list): keys
            })

class Has(Association):
    """
    Builds the association scope for a C{has} association. This is the
    superclass for L{HasOne} and L{HasMany} associations. The only difference
    between a has one and has many relation, is that C{.first()} is called on
    the has one association's scope but not on the has many association's
    scope. See the L{Association} class for more details on how associations
    work.

    """

    # Foreign key attributes
    def get_foreign_key(self):
        if super(Has, self).foreign_key:
            return super(Has, self).foreign_key
        elif self.polymorphic():
            return '%s_id' % self.options['as_']
        else:
            return '%s_id' % self.target_klass.__name__.lower()

    def set_foreign_key(self, value):
        self.options['foreign_key'] = value
    foreign_key = property(get_foreign_key, set_foreign_key)

    def polymorphic(self):
        return self.options.has_key('as_')

    def polymorphic_type(self):
        return '%s_type' % self.options['as_']

    def scope(self, obj_or_list):
        """
        Returns a scope on the source class containing this association

        Builds conditions on top of the base_scope generated from any finder
        options set with the association::

            widgets = HasMany(klass=Widget, foreign_key='widget_id')
            comments = HasMany(as_='parent')

        In addition to any finder options included with the association options
        the following will be added::

            where(widget_id=target['id'])

        Or for the polymorphic :comments association::

            where(parent_id=target['id'], parent_type=target.class)

        """
        pk_attr = self.primary_key()
        if isinstance(obj_or_list, pyperry.Base):
            keys = obj_or_list[pk_attr]
            obj = obj_or_list
        else:
            keys = [o[pk_attr] for o in obj_or_list]
            obj = obj_or_list[0]

        if keys is not None:
            scope = self._base_scope(obj_or_list).where({
                self.foreign_key: keys
            })
            if self.polymorphic():
                scope = scope.where({
                    self.polymorphic_type(): obj.__class__.__name__
                })
            return scope

def HasMany(**kwargs):
    """
    Wrapper constructor to detect through relationships and initialize the
    correct class
    """
    if kwargs.get('through') is not None:
        return HasManyThrough(**kwargs)
    else:
        return HasManyDirectly(**kwargs)

class HasManyDirectly(Has):
    """
    The C{HasManyDirectly} class simply declares that the L{Has} association is
    a collection of type C{'has_many'}.

    """
    def type(self):
        return 'has_many'

    def collection(self):
        return True

class HasOne(Has):
    """
    The C{HasOne} class simply declares that the L{Has} association is a
    not a collection and has a type of C{'has_one'}.

    """
    def type(self):
        return 'has_one'

    def collection(self):
        return False

class HasManyThrough(Has):
    """
    The C{HasManyThrough} class is used whenever a C{has_many} association is
    created with the C{through} option. It works by using the association id
    given with the through option as a I{proxy} association to another class
    on which a I{source} association is defined. The source class for a has
    many through association will be the source class of the source
    association. This means that the scope for a has many through association
    is actually two scopes chained together. The proxy scope is used to
    retrieve the records on which to build the source association, which is
    used to build a scope for the records represented by the has many through
    association. The proxy and source associations may be any of the simple has
    or belongs to association types.

    B{Options specific to has many through associations}

        - B{through}: the association id of an association defined on the
          target class. This association will be used as the proxy association,
          and it is an error if this association does not exist.

        - B{source}: the id of the source association. If the source option is
          not specified, we assume that the source association's id is the same
          as the has many through association's id.

        - B{source_type}: the name of the source class as a string. This option
          may be required if the source class is ambiguous, such as when the
          source association is a polymorphic belongs_to association.

    B{Has many through example}

    This example shows how to create a basic has many through relationship in
    which the internet has many connected devices through its networks. The has
    many through association is defined on the Internet class. Notice how the
    proxy association, C{networks}, is defined on the target class,
    C{Internet}, and the source association, C{devices}, is defined on the
    proxy association's source class, C{Network}. Therefore, the source class
    for the entire relation is the source association's source class,
    C{Device}::

        class Internet(pyperry.Base):
            id = Field()

            connected_devices = HasMany(through'networks', source='devices')
            networks = HasMany(class_name='Network')

        class Network(pyperry.Base):
            id = Field()
            internet_id = Field()

            internet = BelongsTo(class_name='Internet')
            devices = HasMany(class_name='Device')

        class Device(pyperry.Base):
            id = Field()
            network_id = Field()

            network = BelongsTo(class_name='Network')
    """
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
                    source.primary_key())

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

