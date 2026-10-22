# 빌드 컨텍스트: 저장소 루트
FROM image-registry.openshift-image-registry.svc:5000/openshift/cli:latest AS cli

FROM registry.access.redhat.com/ubi9/python-311:latest

USER 0
COPY --from=cli /usr/bin/oc /usr/local/bin/oc
RUN git --version
COPY ops/requirements.txt /opt/app-root/src/requirements.txt
RUN pip install --no-cache-dir -r /opt/app-root/src/requirements.txt
COPY ops/app /opt/app-root/src/app
RUN chown -R 1001:0 /opt/app-root/src && chmod -R g=u /opt/app-root/src

USER 1001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
