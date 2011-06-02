from pyperry.errors import AssociationNotFound

class PreloadAssociations(object):

    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        results = self.next(**kwargs)
        if kwargs['mode'] == 'read' and len(results) > 0:
            self.do_preload(results, **kwargs)
        return results

    def do_preload(self, results, **kwargs):
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
