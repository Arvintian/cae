from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import traceback

Base = declarative_base()


class ModelMiddleware(object):

    def __init__(self, get_response, app):
        self.current_app = app
        self.get_response = get_response
        app_config: dict = app.config
        # One-time configuration and initialization.
        self.config = {
            "SQLALCHEMY_DATABASE_URI": app_config.get("SQLALCHEMY_DATABASE_URI"),
            "SQLALCHEMY_ECHO": app_config.get("SQLALCHEMY_ECHO", False),
            "SQLALCHEMY_COMMIT_ON_TEARDOWN": app_config.get("SQLALCHEMY_COMMIT_ON_TEARDOWN", False),
            "SQLALCHEMY_ENGINE_OPTIONS": app_config.get("SQLALCHEMY_ENGINE_OPTIONS", {}),
        }
        self.engine = create_engine(self.config["SQLALCHEMY_DATABASE_URI"], echo=self.config["SQLALCHEMY_ECHO"], **self.config["SQLALCHEMY_ENGINE_OPTIONS"])
        self.SessionMaker = sessionmaker(bind=self.engine)
        app.logger.debug("INIT SQLALCHEMY_DATABASE_URI {}".format(self.config["SQLALCHEMY_DATABASE_URI"]))

    def __call__(self, request):
        try:
            # Code to be executed for each request before
            # the view (and later middleware) are called.
            ds = self.SessionMaker()
            setattr(request, "ds", ds)

            # exec
            response = self.get_response(request)

            # Code to be executed for each request/response after
            # the view is called.
            if self.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"]:
                ds.commit()

            ds.close()

            return response
        except Exception as e:
            self.current_app.logger.error(traceback.format_exc())
            return self.current_app.make_response(request, {
                "code": -1,
                "msg": "{}".format(e)
            })
