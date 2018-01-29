SOURCE=.
IMAGENAME=m3h7/coinlendingbot
RELEASE=v$(shell date +%y%j)

.PHONY: all
all: usage

usage:
	@echo "CoinLendingBot Build and Push"
	@echo "Usage:"
	@echo "  make pull				- Pull base image from Docker hub"
	@echo "  make build				- Build the Docker image"
	@echo "  make REGISTRY=\"myregistry:5000\" push	- Push image to registry"
	@echo ""
	@echo "Change registry and image name in Makefile before build and push."

pull:
	docker pull python:3.6-slim

build:
	docker build --tag $(IMAGENAME) $(SOURCE)
	docker tag $(IMAGENAME) $(IMAGENAME):$(RELEASE)

push: build
	docker tag $(IMAGENAME) $(REGISTRY)/$(IMAGENAME)
	docker tag $(IMAGENAME):$(RELEASE) $(REGISTRY)/$(IMAGENAME):$(RELEASE)
	docker push $(REGISTRY)/$(IMAGENAME)
	docker push $(REGISTRY)/$(IMAGENAME):$(RELEASE)
