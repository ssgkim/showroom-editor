# 빌드 컨텍스트: 저장소 루트 (통합 Antora 차트를 이미지에 포함한다)
FROM image-registry.openshift-image-registry.svc:5000/openshift/cli:latest AS cli

FROM registry.access.redhat.com/ubi9/python-311:latest

ARG HELM_VERSION=v3.17.3
USER 0
RUN curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" | tar -xz -C /tmp \
 && mv /tmp/linux-amd64/helm /usr/local/bin/helm \
 && rm -rf /tmp/linux-amd64 \
 && git --version && helm version --short
COPY --from=cli /usr/bin/oc /usr/local/bin/oc

COPY Chart.yaml values.yaml .helmignore /opt/chart/
COPY templates /opt/chart/templates
COPY files /opt/chart/files

COPY editor/requirements.txt /opt/app-root/src/requirements.txt
RUN pip install --no-cache-dir -r /opt/app-root/src/requirements.txt
COPY editor/app /opt/app-root/src/app
RUN chown -R 1001:0 /opt/app-root/src && chmod -R g=u /opt/app-root/src

USER 1001
ENV CHART_DIR=/opt/chart \
    HELM_CACHE_HOME=/tmp/helm/cache \
    HELM_CONFIG_HOME=/tmp/helm/config \
    HELM_DATA_HOME=/tmp/helm/data
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
