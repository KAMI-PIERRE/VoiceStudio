FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    VOICE_STUDIO_HOSTED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    PORT=7860 \
    VOICE_STUDIO_MODEL_DIR=/home/user/.cache/voice-studio/models \
    VOICE_STUDIO_OUTPUT_DIR=/tmp/voice-studio/outputs

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user

WORKDIR /home/user/app
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt

COPY --chown=user:user app.py characters.py voice_engine.py studio_ui.py runtime_config.py ./
COPY --chown=user:user assets ./assets
USER user
RUN python app.py --download-model

EXPOSE 7860
CMD ["python", "-u", "app.py"]
