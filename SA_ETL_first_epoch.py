import parsers.ETL_parser as ETL


import argparse

parser = argparse.ArgumentParser(prog='Standalone ETL First Event Epoch Millisecond Extractor')
parser.add_argument('-i', '--input', help='ETL file Path')
args = parser.parse_args()


def main (etl_path) :
    ETL.parseETL(etl_path, {})
        


main(args.input)