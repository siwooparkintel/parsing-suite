@echo off
:: Run focused test suite for ParseAll.py and Collection_Parser.py
cd /d "%~dp0"

python -m pytest test/test_parseall.py test/test_collection_parser.py -v --tb=short 2>&1
