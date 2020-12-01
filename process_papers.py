import argparse
import logging
import re

from wbtools.db.dbmanager import WBDBManager
from wbtools.db.generic import WBGenericDBManager
from wbtools.lib.nlp import get_new_variations_from_text, NEW_VAR_REGEX, PaperSections
from wbtools.literature.corpus import CorpusManager
from wbtools.lib.scraping import get_cgc_allele_designations

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Build corpus from WB papers and calculate similarity between "
                                                 "articles")
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
    parser.add_argument("-m", "--model", metavar="model_path", dest="model_path", type=str)
    parser.add_argument("-d", "--from-date", metavar="from_date", dest="from_date", type=str,
                        help="use only articles included in WB at or after the specified date")
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=args.log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s:%(message)s')

    cm = CorpusManager()
    cm.load_from_wb_database(args.db_name, args.db_user, args.db_password, args.db_host,
                             tazendra_ssh_user=args.tazendra_ssh_user, tazendra_ssh_passwd=args.tazendra_ssh_password,
                             from_date=args.from_date, load_curation_info=True, max_num_papers=10,
                             paper_ids=["00054758", "00054762", "00054766", "00054772", "00054777", "00054789",
                                        "00054790", "00054792"])
    db_manager = WBGenericDBManager(dbname=args.db_name, user=args.db_user, password=args.db_password, host=args.db_host)
    curated_alleles = db_manager.get_curated_variations(exclude_id_used_as_name=True)
    print("PAPER_ID", "ALLELE_NAME", "TYPE", "SVM_VALUE", "NUM_MATCHES_IN_SENTENCE", "SENTENCE", sep="\t")
    for paper in cm.corpus.values():
        full_text = " ".join(paper.get_text_docs(include_supplemental=True, remove_sections=[PaperSections.REFERENCES],
                                                 must_be_present=[PaperSections.RESULTS],
                                                 split_sentences=False, lowercase=False, tokenize=False,
                                                 remove_stopwords=False, remove_alpha=False))
        sentences = paper.get_text_docs(include_supplemental=True, remove_sections=[PaperSections.REFERENCES],
                                        must_be_present=[PaperSections.RESULTS],
                                        split_sentences=True, lowercase=False, tokenize=False, remove_stopwords=False,
                                        remove_alpha=False)
        svm_value = paper.svm_values["seqchange"]
        extracted_alleles = get_new_variations_from_text(full_text)
        extracted_alleles = [allele for allele in extracted_alleles if allele[0] not in curated_alleles]
        if svm_value:
            for allele, suspicious in extracted_alleles:
                allele_regex = r".*[ \(]" + allele + r"[ \)\[].*"
                matching_sentences = [sentence for sentence in sentences if re.match(allele_regex, sentence)]
                for matching_sentence in matching_sentences:
                    count = len(re.findall(allele_regex, matching_sentence))
                    print(paper.paper_id, allele, suspicious, svm_value, count, matching_sentence, sep="\t")


if __name__ == '__main__':
    main()
