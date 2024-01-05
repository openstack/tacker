FROM python:3.8.13

## setup and run
# [usage:]
# docker build -t tacker-monitoring-test .
# docker run -v ${PWD}/src:/work/src -v ${PWD}/rules:/etc/prometheus/rules -p 55555:55555 -p 50022:22 -e TEST_REMOTE_URI="http://<nfvo_addr>:<port>" -it tacker-monitoring-test
#
# (under proxy environment)
# sudo docker build --build-arg PROXY=$http_proxy -t tacker-monitoring-test .
# docker run -v ${PWD}/src:/work/src -v ${PWD}/rules:/etc/prometheus/rules -p 55555:55555 -p 50022:22 -e TEST_REMOTE_URI="http://<nfvo_addr>:<port>" -it tacker-monitoring-test
#
# [api:]
# curl -X POST http://<<this_tool's_url>>:55555/v2/tenant_id/servers/server_id/alarms -d '{"fault_action": "http://<<tacker_uri>>", "fault_id": "2222"}' -i
# curl -X DELETE http://<<this_tool's_url>>:55555/v2/tenant_id/servers/server_id/alarms/<<alarm_id>> -i

ARG PROXY
ENV http_proxy ${PROXY}
ENV https_proxy ${PROXY}
ENV HTTP_PROXY ${PROXY}
ENV HTTPS_PROXY ${PROXY}

USER root
RUN useradd -m user
RUN if [ ! -z "${MS_UID}" -a "${MS_UID}" -ge 1000 ] ;\
         then usermod -u ${MS_UID} user ;\
         else usermod -u 1000 user ; \
    fi

# SSH server
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server && \
    rm -rf /var/lib/apt/lists/* && \
    echo "root:root" | chpasswd && \
    sed -i "s/#PermitRootLogin prohibit-password/PermitRootLogin yes/" /etc/ssh/sshd_config

RUN pip install --upgrade pip
COPY requirements.txt /tmp/requirements.txt
RUN pip install --default-timeout=1000 --no-cache-dir -r /tmp/requirements.txt
COPY entrypoint.sh /tmp/entrypoint.sh
RUN mkdir -p /work/src && chmod 777 /work/src
RUN mkdir -p /etc/prometheus/rules && chmod 777 /etc/prometheus/rules

# prometheus & promtool
ARG PROM_VERSION="2.45.3"
RUN cd /tmp && \
    wget -q https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz && \
    tar zxf /tmp/prometheus-${PROM_VERSION}.linux-amd64.tar.gz -C /usr/local/src/&& \
    ln -s /usr/local/src/prometheus-${PROM_VERSION}.linux-amd64/prometheus /usr/bin/prometheus && \
    ln -s /usr/local/src/prometheus-${PROM_VERSION}.linux-amd64/promtool /usr/bin/promtool

ENV http_proxy ''
ENV https_proxy ''
ENV HTTP_PROXY ''
ENV HTTPS_PROXY ''

EXPOSE 55555
EXPOSE 22

#USER user
WORKDIR /work
RUN chown "user:user" /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh
CMD [ "/tmp/entrypoint.sh" ]
