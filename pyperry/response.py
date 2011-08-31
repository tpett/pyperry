import pyperry.response_parsers as parsers

class Response(object):
    """
    Used to transport response data from a write adapter through the
    adapter's call stack.

    A write adapter returns a C{Response} object for all calls to its C{write}
    or C{delete} methods. The write adapter is responsible for setting the
    C{success}, C{raw}, C{raw_format}, C{status}, and C{meta} attributes on the
    C{Response} object, but should perform no additional processing.
    Middlewares can then use the response data to modify the model being saved.
    For example, after a write, one middleware may refresh the model's
    attributes, while another middleware may expire some cache entries for that
    model. The C{parsed}, C{model_attributes}, and C{errors} methods are
    provided to return the response data in formats that are easy for
    middlewares to work with.

    """

    PARSERS = {
        'json': parsers.JSONResponseParser
    }

    def __init__(self, **kwargs):

        self.success = False
        """True if the write or delete succeeded, False otherwise"""

        self.status = None
        """an adapter-specific status code (optional)"""

        self.meta = {}
        """adapter-specific information about the response (optional)"""

        self.raw = None
        """the raw (unmodified) response data received from the adapter"""

        self.raw_format = 'json'
        """the data format of the raw response data, such as 'json' or 'xml'"""

        for k, v in kwargs.items():
            self.__setattr__(k, v)

    def parsed(self):
        """
        Returns a format-independent dictionary representation of the raw
        response data. Both the model_attributes and errors methods transform
        the result of the parsed method into a form that is meaningful.

        """
        if not hasattr(self, '_parsed'):
            parser = self.PARSERS[self.raw_format]()
            self._parsed = None
            if self.raw is not None:
                try:
                    self._parsed = parser.parse(self.raw)
                except:
                    pass # return None if raw could not be parsed
        return self._parsed

    def model_attributes(self):
        """
        Returns a dictionary representing a model's attributes obtained by
        transforming the result of the parsed method.

        """
        if hasattr(self, '_model_attributes'):
            return self._model_attributes

        parsed = self.parsed()
        if isinstance(parsed, dict):
            if len(parsed) == 1 and isinstance(parsed.values()[0], dict):
                self._model_attributes = parsed[parsed.keys()[0]]
            else:
                self._model_attributes = parsed
        else:
            self._model_attributes = {}
        return self._model_attributes

    def errors(self):
        """
        Returns a dictionary in the same format as the model's errors
        dictionary obtained by transforming the result of the parsed method.

        """
        parsed = self.parsed()
        if isinstance(parsed, dict):
            if 'errors' in parsed and isinstance(parsed['errors'], dict):
                errors = parsed['errors']
            else:
                errors = parsed
        else:
            errors = {}
        return errors

    def __setattr__(self, name, value):
        """
        Prevent the parsed method from being replaced.

        Allows a user to set response.parsed = {...} without replacing the
        parsed method. This is because the parsed method will parse the
        contents of the raw attribute and store its value in the _parsed
        attribute if _parsed has not already been set to some other value.
        Setting any other attribute still works like normal.

        """
        if name == 'parsed':
            name = '_' + name
        object.__setattr__(self, name, value)
