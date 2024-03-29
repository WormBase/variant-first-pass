import argparse
import logging
import smtplib
from collections import defaultdict
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from wbtools.db.generic import WBGenericDBManager
from wbtools.lib.nlp.common import PaperSections, EntityType
from wbtools.lib.nlp.entity_extraction.ntt_extractor import NttExtractor
from wbtools.lib.nlp.entity_extraction.variations import is_new_variation_to_exclude, is_variation_suspicious
from wbtools.literature.corpus import CorpusManager

logger = logging.getLogger(__name__)


def send_email(subject, content, recipients, server_host, server_port, email_user, email_passwd, attachment):
    body = MIMEText(content, "html", _charset='utf-8')
    msg = MIMEMultipart()
    msg.attach(body)

    csv_file = MIMEApplication(attachment, "text/csv")
    csv_file.add_header('Content-Disposition', 'attachment', filename='results.csv')
    msg.attach(csv_file)
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
    parser.add_argument("-x", "--exclude-ids-file", metavar="exclude_ids_file", dest="exclude_ids_file", type=str,
                        default=None)
    parser.add_argument("-y", "--exclude-pap-types", metavar="exclude_pap_types", dest="exclude_pap_types", nargs="*",
                        type=str, default=None)

    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=args.log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s:%(message)s')

    if args.exclude_ids_file:
        Path(args.exclude_ids_file).touch()
    cm = CorpusManager()
    cm.load_from_wb_database(
        args.db_name, args.db_user, args.db_password, args.db_host, from_date=args.from_date,
        max_num_papers=args.max_num_papers,
        exclude_ids=[line.strip() for line in open(args.exclude_ids_file)] if args.exclude_ids_file else None,
        must_be_autclass_flagged=True, exclude_pap_types=args.exclude_pap_types)
    remove_sections = [PaperSections.INTRODUCTION, PaperSections.REFERENCES]
    must_be_present = [PaperSections.RESULTS]
    if cm.size() > 0:
        db_manager = WBGenericDBManager(dbname=args.db_name, user=args.db_user, password=args.db_password,
                                        host=args.db_host)
        results = "PAPER_ID&emsp;VARIANT_NAME&emsp;TYPE&emsp;SVM_VALUE&emsp;NUM_MATCHES_IN_PAPER&emsp;" \
                  "STRAINS_IN_MATCHED_SENTENCES&emsp;MATCHED_SENTENCES<br/><br/>"
        results_attachment = "\t".join(["PAPER_ID", "VARIANT_NAME", "TYPE", "SVM_VALUE", "NUM_MATCHES_IN_PAPER",
                                        "STRAINS_IN_MATCHED_SENTENCES", "MATCHED_SENTENCES"]) + "\n"
        ntt_extractor = NttExtractor(db_manager=db_manager)
        for paper in cm.get_all_papers():
            sentences = paper.get_text_docs(include_supplemental=True, remove_sections=remove_sections,
                                            must_be_present=must_be_present,
                                            split_sentences=True, lowercase=False, tokenize=False,
                                            remove_stopwords=False, remove_alpha=False)
            aut_class_value = paper.get_aut_class_value_for_datatype("seqchange")
            allele_matches = defaultdict(list)
            allele_suspicious = defaultdict(bool)
            allele_strains = defaultdict(set)
            for sentence in sentences:
                new_alleles = ntt_extractor.extract_all_entities_by_type(text=sentence,
                                                                         entity_type=EntityType.VARIATION,
                                                                         exclude_curated=True)
                new_alleles = [allele for allele in new_alleles if not is_new_variation_to_exclude(allele)]
                for allele in new_alleles:
                    allele_matches[allele].append("\"" + sentence.replace("\n", " ") + "\"")
                    allele_suspicious[allele] = is_variation_suspicious(allele)
                    allele_strains[allele].update(ntt_extractor.extract_all_entities_by_type(
                        text=sentence, entity_type=EntityType.STRAIN, match_curated=True))
            for allele, matching_sentences in allele_matches.items():
                results += "&emsp;".join([f"<a href=\"http://tazendra.caltech.edu/~postgres/cgi-bin/curation_status.c"
                                          f"gi?select_curator=two1823&select_datatypesource=caltech&specific_papers="
                                          f"{paper.paper_id}&select_topic=none&checkbox_newmutant=newmutant&checkbox_"
                                          f"oa=on&checkbox_cur=on&checkbox_svm=on&checkbox_str=on&checkbox_afp=on&che"
                                          f"ckbox_cfp=on&papers_per_page=10&checkbox_journal=on&checkbox_pmid=on&chec"
                                          f"kbox_pdf=on&action=Get+Results\">{paper.paper_id}</a>",
                                          allele, allele_suspicious[allele], aut_class_value,
                                          str(len(matching_sentences)), " ".join(allele_strains[allele]) if
                                          allele_strains[allele] else "No Strains Found",
                                          " ".join(matching_sentences)]) + "<br/>"
                results_attachment += "\t".join([paper.paper_id, allele, allele_suspicious[allele], aut_class_value,
                                                 str(len(matching_sentences)), " ".join(allele_strains[allele]) if
                                                 allele_strains[allele] else "No Strains Found",
                                                 " ".join(matching_sentences)]) + "\n"

        with open(args.exclude_ids_file, 'a') as exclude_ids_file:
            for paper in cm.get_all_papers():
                exclude_ids_file.write(paper.paper_id + "\n")

        send_email(subject=("[Test] " if args.testing else "") + "[Variant First Pass] New Results",
                   content=results, recipients=[args.email_recipient], server_host=args.email_host,
                   server_port=args.email_port, email_user=args.email_user, email_passwd=args.email_password,
                   attachment=results_attachment)
    logger.info("Pipeline finished successfully")


if __name__ == '__main__':
    main()
