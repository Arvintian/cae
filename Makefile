REGISTRY = arvintian
PROJECT = cae
API_VERSION = 1.2.0
UI_VERSION = 1.0.1

all: api ui

api:
	docker build -t $(REGISTRY)/$(PROJECT)-api:$(API_VERSION) .

ui:
	cd webui && npm run build
	docker build -t $(REGISTRY)/$(PROJECT)-ui:$(UI_VERSION) ./webui/

publish-api:
	docker push $(REGISTRY)/$(PROJECT)-api:$(API_VERSION)

publish-ui:
	docker push $(REGISTRY)/$(PROJECT)-ui:$(UI_VERSION)

publish:
	docker push $(REGISTRY)/$(PROJECT)-api:$(API_VERSION)
	docker push $(REGISTRY)/$(PROJECT)-ui:$(UI_VERSION)

clean:
	docker images | grep -E "$(PROJECT)" | awk '{print $$3}' | uniq | xargs -I {} docker rmi --force {}