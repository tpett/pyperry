import json

class ResponseParser(object):
    """
    Base class for all response parsers

    All subclasses should implement the parse method. To make your parser
    available to the Response class, you must add it to the Response.PARSERS
    dictionary using the format as the key.

    """
    def parse(self, raw_str):
        """
        Returns a transformation of the raw response into native python objects

        """
        raise NotImplemented


class JSONResponseParser(ResponseParser):
    def parse(self, raw_str):
        return json.loads(raw_str)
