#! /bin/bash

docker build --label "io.docker.server.metadata=$(cat server-metadata.yaml)" -t manim-mcp:latest .  
