from pyperry.errors import AssociationNotFound

class PreloadAssociations(object):
    """
    The PreloadAssociations processor looks for any association ids given in
    a query's 'includes' value and eager loads those associations. The purpose
    of eager loading (or preloading) is to reduce the number of adapter calls
    needed to retrieve records in an association, which can yield a significant
    performance boost if you have a query where you are using many associated
    models.

    For example, let's assume you are writing a news website and you have
    a Reporter model and a Story model where each Reporter has many Stories.
    Now suppose you want to display a list all reporters and their stories on
    the screen grouped by the reporter's name, you could do this like::

        reporters = Reporter.order('name').all()
        for reporter in reporters:
            print reporter.name
            for story in reporter.stories():
                print "\t%s" % story.title

    If your news website has 20 reporters, you have just executed 1 adapter
    call to retrieve the list of reporters and then 20 more adapter calls, one
    for each reporter's stories, for a total of 21 adapter calls. The problem
    with having too many adapter calls is that typically adapters must read
    data from a server on the network, which causes your program to wait while
    the server generates a response and sends it over the network.

    Instead, you can achieve the same results in 2 queries by using the
    includes method in your query to trigger association preloading. In this
    modified example, we simple add C{.includes('stories')} to our query, and
    all of the stories for every report will be retrieved with only one
    additional adapter call::

        reporters = Reporter.order('name').includes('stories').all()
        for reporter in reporters:
            print reporter.name
            for story in reporter.stories():
                print " - %s" % story.title

    """
    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        results = self.next(**kwargs)
        if kwargs['mode'] == 'read' and len(results) > 0:
            self.do_preload(results, **kwargs)
        return results

    def do_preload(self, results, **kwargs):
        """
        Eager loads the records for each association in the query's includes.

        """
        rel = kwargs['relation']
        includes = rel.query().get('includes') or {}

        for association_id in includes.keys():
            association = rel.klass.defined_associations.get(association_id)
            if association is None: raise AssociationNotFound(
                    "unkown association: %s" % association_id)
            scope = association.scope(results)
            scope = scope.includes(includes[association_id])
            eager_records = scope.all({'modifiers': rel.modifiers_value()})

            for result in results:
                self.add_records_to_scope(association, eager_records, result)

    def add_records_to_scope(self, association, records, result):
        """
        Caches the eager loaded records on the matching target model and
        association along with the corresponding scope.

        """
        scope = association.scope(result)
        pk = association.primary_key()
        fk = association.foreign_key

        if association.type() is 'belongs_to':
            scope._records = [record for record in records if
                             getattr(record, pk) == getattr(result, fk)]

        else: # has_one, has_many
            scope._records = [record for record in records if
                             getattr(record, fk) == getattr(result, pk)]

        scope_value = scope
        if not association.collection():
            scope_value = scope._records[0] if len(scope._records) > 0 else None

        setattr(result, association.id, scope_value)
