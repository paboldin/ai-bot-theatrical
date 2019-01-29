#!/bin/sh -ex

mkdir -p model
(cd model; wget http://vectors.nlpl.eu/repository/11/180.zip -c; unzip 180.zip)
