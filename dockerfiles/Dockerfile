FROM birkbeckctp/doab-base
ADD ./ /vol/app
WORKDIR /vol/app
RUN pip3 install -e /vol/app
ENTRYPOINT ["doab"]

