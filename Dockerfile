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
ENV TAZENDRA_SSH_USER=""
ENV TAZENDRA_SSH_PASSWD=""
ENV FROM_DATE="1970-01-01"
ENV EMAIL_USER=""
ENV EMAIL_HOST=""
ENV EMAIL_PORT=""
ENV EMAIL_PASSWD=""
ENV EMAIL_RECIPIENT=""
ENV EXCLUDE_IDS_FILE=""
ENV EXCLUDE_PAP_TYPES=""


ADD crontab /etc/cron.d/vfp-cron
RUN chmod 0644 /etc/cron.d/vfp-cron
RUN touch /var/log/vfp_pipeline.log
RUN crontab /etc/cron.d/vfp-cron

ENV PYTHONPATH=$PYTHONPATH:/usr/src/app/

CMD echo $DB_HOST > /etc/vfp_db_host && \
    echo $DB_NAME > /etc/vfp_db_name && \
    echo $DB_USER > /etc/vfp_db_user && \
    echo $DB_PASSWD > /etc/vfp_db_passwd && \
    echo $MAX_NUM_PAPERS > /etc/vfp_max_num_papers && \
    echo $TAZENDRA_SSH_USER > /etc/vfp_tazendra_ssh_user && \
    echo $TAZENDRA_SSH_PASSWD > /etc/vfp_tazendra_ssh_passwd && \
    echo $FROM_DATE > /etc/vfp_from_date && \
    echo $EMAIL_USER > /etc/vfp_email_user && \
    echo $EMAIL_HOST > /etc/vfp_email_host && \
    echo $EMAIL_PORT > /etc/vfp_email_port && \
    echo $EMAIL_PASSWD > /etc/vfp_email_passwd && \
    echo $EMAIL_RECIPIENT > /etc/vfp_email_recipient && \
    echo $EXCLUDE_IDS_FILE > /etc/vfp_exclude_ids_file && \
    echo $EXCLUDE_PAP_TYPES > /etc/vfp_exclude_pap_types && \
    cron && tail -f /dev/null