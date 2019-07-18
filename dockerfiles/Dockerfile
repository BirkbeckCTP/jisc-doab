FROM python:3.7
ADD ./ /vol/app
WORKDIR /vol/app
RUN pip3 install psycopg2-binary
RUN pip3 install -e /vol/app
ENTRYPOINT ["doab"]

