from pretty_logging import pretty_logger
import traceback


class PanicMiddleware(object):

    def __init__(self, get_response, app):
        self.current_app = app
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, callback, callback_kwargs):
        return None

    def process_exception(self, request, exception):
        pretty_logger.error(traceback.format_exc())
        return {
            "code": -1,
            "msg": "{}".format(exception)
        }
