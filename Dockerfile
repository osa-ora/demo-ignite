FROM registry.access.redhat.com/ubi9/python-312:latest

USER root

RUN dnf install -y git tar gzip ca-certificates && dnf clean all

ARG KUBECTL_VERSION=v1.30.3
RUN curl -L -o /usr/local/bin/kubectl \
    https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
    && chmod +x /usr/local/bin/kubectl

ARG OC_VERSION=4.15.0
RUN curl -L https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OC_VERSION}/openshift-client-linux.tar.gz \
    | tar -xz -C /usr/local/bin oc

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN chown -R 1001:0 /app && chmod -R g=u /app

USER 1001

CMD ["python", "main.py"]
