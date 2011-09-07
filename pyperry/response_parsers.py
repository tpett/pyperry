try:
    import json
except ImportError:
    import simplejson as json

class ResponseParser(object):
    """
    This is the base class for all response parsers.

    All subclasses should implement the C{parse} method. To make your parser
    available to the L{Response} class, you must add it to the
    C{Response.PARSERS} dict using the format ('json', 'xml', etc.) as the key.

    """
    def parse(self, raw_str):
        """
        Returns a transformation of the raw response into native python objects

        """
        raise NotImplemented


class JSONResponseParser(ResponseParser):
    """
    A L{ResponseParser} for reponses in JSON format C{(format='json')}.

    """

    def parse(self, raw_str):
        return json.loads(raw_str)
