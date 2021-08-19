from cae.config import config
from cae.controllers import bp_instance, bp_ingress, bp_image
from madara.app import Madara

app = Madara(config=config)

app.register_blueprint(bp_instance, url_prefix="/api/instance")
app.register_blueprint(bp_image, url_prefix="/api/image")
app.register_blueprint(bp_ingress, url_prefix="/api/ingress")
