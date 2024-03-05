#!/usr/bin/env bash

microk8s helm3 repo add t3n https://storage.googleapis.com/t3n-helm-charts
microk8s helm3 install mosquitto t3n/mosquitto --version 2.4.1 --values values.yaml
