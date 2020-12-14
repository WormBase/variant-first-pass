import argparse
import logging
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from wbtools.db.generic import WBGenericDBManager
from wbtools.lib.nlp import get_new_variations_from_text, PaperSections
from wbtools.literature.corpus import CorpusManager


logger = logging.getLogger(__name__)


def send_email(subject, content, recipients, server_host, server_port, email_user, email_passwd):
    body = MIMEText(content, "html")
    msg = MIMEMultipart('alternative')
    msg.attach(body)
    msg['Subject'] = subject
    msg['From'] = "outreach@wormbase.org"
    msg['To'] = ", ".join(recipients)

    try:
        server_ssl = smtplib.SMTP_SSL(server_host, server_port)
        server_ssl.login(email_user, email_passwd)
        server_ssl.send_message(msg)
        logger.info("Email sent to: " + ", ".join(recipients))
        server_ssl.quit()
    except:
        logger.fatal("Can't connect to smtp server. Email not sent.")


def main():
    parser = argparse.ArgumentParser(description="Variant First Pass")
    parser.add_argument("-N", "--db-name", metavar="db_name", dest="db_name", type=str)
    parser.add_argument("-U", "--db-user", metavar="db_user", dest="db_user", type=str)
    parser.add_argument("-P", "--db-password", metavar="db_password", dest="db_password", type=str, default="")
    parser.add_argument("-H", "--db-host", metavar="db_host", dest="db_host", type=str)
    parser.add_argument("-w", "--tazendra-ssh-username", metavar="tazendra_ssh_user", dest="tazendra_ssh_user",
                        type=str)
    parser.add_argument("-z", "--tazendra_ssh_password", metavar="tazendra_ssh_password", dest="tazendra_ssh_password",
                        type=str)
    parser.add_argument("-l", "--log-file", metavar="log_file", dest="log_file", type=str, default=None,
                        help="path to log file")
    parser.add_argument("-L", "--log-level", dest="log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                                                        'CRITICAL'], default="INFO",
                        help="set the logging level")
    parser.add_argument("-d", "--from-date", metavar="from_date", dest="from_date", type=str,
                        help="use only articles included in WB at or after the specified date")
    parser.add_argument("-o", "--email-host", metavar="email_host", dest="email_host", type=str)
    parser.add_argument("-r", "--email-port", metavar="email_port", dest="email_port", type=int)
    parser.add_argument("-u", "--email-user", metavar="email_user", dest="email_user", type=str)
    parser.add_argument("-p", "--email-password", metavar="email_password", dest="email_password", type=str)
    parser.add_argument("-e", "--email-recipient", metavar="email_recipient", dest="email_recipient", type=str)
    parser.add_argument("-t", "--testing", action="store_true")
    parser.add_argument("-m", "--max-num-papers", metavar="max_num_papers", dest="max_num_papers", type=int)

    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=args.log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s:%(message)s')

    cm = CorpusManager()
    cm.load_from_wb_database(args.db_name, args.db_user, args.db_password, args.db_host,
                             tazendra_ssh_user=args.tazendra_ssh_user, tazendra_ssh_passwd=args.tazendra_ssh_password,
                             from_date=args.from_date, max_num_papers=args.max_num_papers, must_have_svm=True)
    remove_sections = [PaperSections.INTRODUCTION, PaperSections.REFERENCES]
    must_be_present = [PaperSections.RESULTS]
    if cm.size() > 0:
        db_manager = WBGenericDBManager(dbname=args.db_name, user=args.db_user, password=args.db_password,
                                        host=args.db_host)
        curated_alleles = db_manager.get_curated_variations(exclude_id_used_as_name=True)
        results = "PAPER_ID&emsp;VARIANT_NAME&emsp;TYPE&emsp;SVM_VALUE&emsp;NUM_MATCHES_IN_PAPER&emsp;MATCHED_SENTENCES&emsp;LINK_TO_CURATION_STATUS<br/><br/>"
        for paper in cm.corpus.values():
            full_text = " ".join(paper.get_text_docs(include_supplemental=True, remove_sections=remove_sections,
                                                     must_be_present=must_be_present,
                                                     split_sentences=False, lowercase=False, tokenize=False,
                                                     remove_stopwords=False, remove_alpha=False))
            sentences = paper.get_text_docs(include_supplemental=True, remove_sections=remove_sections,
                                            must_be_present=must_be_present,
                                            split_sentences=True, lowercase=False, tokenize=False,
                                            remove_stopwords=False, remove_alpha=False)
            svm_value = paper.svm_values["seqchange"] if paper.svm_values["seqchange"] else "not_yet_classified"
            extracted_alleles = get_new_variations_from_text(full_text)
            extracted_alleles = [allele for allele in extracted_alleles if allele[0] not in curated_alleles]

            for allele, suspicious in extracted_alleles:
                allele_regex = r".*[ \(]" + allele + r"[\. \)\[].*"
                matching_sentences = ",".join(["\"" + sentence + "\"" for sentence in sentences if
                                               re.match(allele_regex, " " + sentence + " ")])
                count = len(re.findall(allele_regex, matching_sentences))
                results += "&emsp;".join([f"<a href=\"http://tazendra.caltech.edu/~postgres/cgi-bin/curation_status.c"
                                          f"gi?select_curator=two1823&select_datatypesource=caltech&specific_papers="
                                          f"{paper.paper_id}&select_topic=none&checkbox_newmutant=newmutant&checkbox_"
                                          f"oa=on&checkbox_cur=on&checkbox_svm=on&checkbox_str=on&checkbox_afp=on&che"
                                          f"ckbox_cfp=on&papers_per_page=10&checkbox_journal=on&checkbox_pmid=on&chec"
                                          f"kbox_pdf=on&action=Get+Results\">{paper.paper_id}</a>",
                                          allele, suspicious, svm_value, str(count), matching_sentences]) + "<br/>"

        send_email(subject=("[Test] " if args.testing else "") + "[Variant First Pass] Results from " + args.from_date +
                                                                 " to " + str(datetime.now().strftime('%Y-%m-%d')),
                   content=results, recipients=[args.email_recipient], server_host=args.email_host,
                   server_port=args.email_port, email_user=args.email_user, email_passwd=args.email_password)


if __name__ == '__main__':
    main()
