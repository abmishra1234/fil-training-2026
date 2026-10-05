# FIL Jenkins Lab image = official Jenkins LTS + Python 3 + the plugins the labs need.
# Pinned LTS for a repeatable classroom. Newer LTS? change the tag (Java 21+ is required).
FROM jenkins/jenkins:2.580.1-lts-jdk21

# --- Python toolchain for the Python pipelines (lint/test/build/deploy run on this controller) ---
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip git curl \
 && rm -rf /var/lib/apt/lists/*
USER jenkins

# --- Skip the setup wizard; configuration comes from Configuration-as-Code (casc/jenkins.yaml) ---
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc/jenkins.yaml

# --- Plugins (latest compatible versions are resolved at build time) ---
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY --chown=jenkins:jenkins casc/jenkins.yaml /usr/share/jenkins/ref/casc/jenkins.yaml
