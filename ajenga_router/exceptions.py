class RouteException(BaseException):
    pass


class RouteFilteredException(RouteException):
    def __init__(self, filter_=lambda _: False):
        super().__init__(filter_)
