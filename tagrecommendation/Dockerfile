FROM freesound:2020-02

RUN mkdir /code
RUN mkdir /tag_recommendation_models
WORKDIR /code

COPY --chown=fsweb:fsweb requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# To avoid installation problems, csc-pysparse needs to be installed after the other packages in requirements.txt
# have been installed. Therefore we install it with a dedicated command here
RUN pip install csc-pysparse==1.1.1.4

COPY --chown=fsweb:fsweb . /code
