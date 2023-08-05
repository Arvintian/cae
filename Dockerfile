FROM python:3.9.17-bullseye

RUN mkdir -p /app /channel
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -U pip && pip install -r /app/requirements.txt
COPY cae /app/cae
ADD main.py /app/

ENTRYPOINT ["python","/app/main.py"]