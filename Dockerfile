FROM python:3.12-slim
# 此 Dockerfile 主要应用于 GitHub Actions 或海外 CI，保留官方源以获得最好连通性

WORKDIR /opt/structalert

ENV PYTHONPATH=/opt/structalert \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt /opt/structalert/requirements.txt
RUN python -m pip install --no-cache-dir -r /opt/structalert/requirements.txt

COPY structalert/ /opt/structalert/structalert/
COPY config/ /opt/structalert/config/

CMD ["python", "-m", "structalert", "run-scheduler", "--config", "/opt/structalert/config/config.yml"]
