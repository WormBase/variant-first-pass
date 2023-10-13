FROM python:3.8-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /usr/src/app/
ADD requirements.txt .
RUN pip3 install -r requirements.txt
RUN python3 -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
COPY . .

ENV DB_HOST=""
ENV DB_NAME=""
ENV DB_USER=""
ENV DB_PASSWD=""
ENV MAX_NUM_PAPERS=50
ENV FROM_DATE="1970-01-01"
ENV EMAIL_USER=""
ENV EMAIL_HOST=""
ENV EMAIL_PORT=""
ENV EMAIL_PASSWD=""
ENV EMAIL_RECIPIENT=""
ENV EXCLUDE_IDS_FILE=""
ENV EXCLUDE_PAP_TYPES=""


ADD crontab /etc/cron.d/vfp-cron

ENV PYTHONPATH=$PYTHONPATH:/usr/src/app/

CMD ["/bin/bash", "startup_script.sh"]
