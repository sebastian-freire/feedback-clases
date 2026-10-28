FROM jenkins/jenkins:lts-jdk21

USER root
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
RUN curl -fsSL -o /usr/local/bin/kubectl https://dl.k8s.io/release/v1.29.15/bin/linux/amd64/kubectl \
    && chmod +x /usr/local/bin/kubectl

RUN jenkins-plugin-cli --plugins configuration-as-code job-dsl workflow-aggregator git credentials-binding
