FROM arvintian/base-image:1.3.1

RUN mkdir -p /app /channel
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r /app/requirements.txt
COPY cae /app/cae
ADD main.py /app/

ENTRYPOINT ["dumb-init","python","/app/main.py"]