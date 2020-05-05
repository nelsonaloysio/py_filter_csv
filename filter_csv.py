#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Filter CSV lines and columns for words or numerical interval.

Allows automatic minimum and maximum date conversion to timestamp.

usage: filter_csv [-h] [-o OUTPUT] [-s STRINGS] [-c COLUMNS] [-m MINIMUM]
                  [-M MAXIMUM] [-a] [-w] [-i] [-v] [-d DELIMITER]
                  [-q {0,1,2,3}] [-e ENCODING] [--index-ignore]
                  input

positional arguments:
  input                 input file name

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        output file name
  -s STRINGS, --strings STRINGS
                        words or file containing list
  -c COLUMNS, --columns COLUMNS
                        column indexes or titles (comma separated)
  -m MINIMUM, --minimum MINIMUM
                        value or date for timestamp (YYYY-MM-DD hh:mm:ss)
  -M MAXIMUM, --maximum MAXIMUM
                        value or date for timestamp (YYYY-MM-DD hh:mm:ss)
  -a, --all-words       match only lines with all strings
  -w, --whole-words     match only lines with whole strings
  -i, --ignore-cases    ignore letter cases such as AaBbCc
  -v, --invert          invert line matching rules
  -d DELIMITER, --delimiter DELIMITER
                        field delimiter (optional)
  -q {0,1,2,3}, --quoting {0,1,2,3}
                        text quoting {0: 'minimal', 1: 'all',
                        2: 'non-numeric', 3: 'none'}
  -e ENCODING, --encoding ENCODING
                        file encoding (default: utf-8)
  --index-ignore        bypass IndexError exceptions
'''

from argparse import ArgumentParser
from csv import reader, writer
from datetime import datetime, timezone
from os.path import basename, isfile, splitext
from re import search
from string import punctuation
from sys import stderr

ENCODING = 'utf-8'

QUOTING = {0: 'minimal',
           1: 'all',
           2: 'non-numeric',
           3: 'none'}

def filter_csv(input_name, output_name=None,
    strings=[], columns=[], minimum=None, maximum=None,
    all_words=False, whole_words=False, ignore_cases=False,
    invert=False, delimiter=None, quoting=0,
    encoding=ENCODING, index_ignore=False):
    '''
    Perform CSV file filtering.
    '''
    filter_columns_only = False

    quotechar = '"'

    if quoting == 3:
        quotechar = ''

    if not output_name:
        name, ext = splitext(basename(input_name))
        output_name = name + '_FILTERED' + ext

    if strings:
        if isinstance(strings, str):
            strings_set = set()
            if isfile(strings):
                strings = load_list(strings)
                print('Loaded', len(strings), 'strings.')
            else:
                strings = strings.split('+')
            for w in strings:
                strings_set.add(w.lower() if ignore_cases else w)
            strings = set(strings_set)

    elif any(x for x in [minimum, maximum]):
        # check for columns
        if not columns:
            print('Error: missing required COLUMNS argument.', file=stderr)
            raise SystemExit
        # set minimum value
        if is_date(minimum):
            minimum = datetime.strptime(date_str_with_time(minimum), '%Y-%m-%d %H:%M:%S')
            minimum = datetime_to_timestamp(minimum)
            print('Minimum timestamp set as %s.' % int(minimum))
        elif is_number(minimum):
            minimum = float(minimum)
        # set maximum value
        if is_date(maximum):
            maximum = datetime.strptime(date_str_with_time(maximum, '23:59:59'), '%Y-%m-%d %H:%M:%S')
            maximum = datetime_to_timestamp(maximum)
            print('Maximum timestamp set as %s.' % int(maximum))
        elif is_number(maximum):
            maximum = float(maximum)

    elif columns:
        filter_columns_only = True

    else:
        print('Error: missing required filter arguments.', file=stderr)
        raise SystemExit

    if isinstance(columns, str):
        columns = columns.replace(', ', ',').split(',')

    if any(x in columns for x in [0, '0']):
        print('Error: invalid column (0), must be >= 1.', file=stderr)
        raise SystemExit

    header_filtered = []
    columns_to_filter = []
    int_lines_matched = 1 # header

    if not delimiter:
        delimiter = get_file_delimiter(input_name, encoding)

    with open(input_name, 'rt', encoding=encoding) as input_file:
        file_reader = reader(input_file, delimiter=delimiter, quoting=quoting)
        header = next(file_reader)

        if strings and not columns:
            columns = header

        for column in columns:
            if isinstance(column, str):
                try: # as index number
                    column = int(column)
                    if column > len(header):
                        print("Error: invalid column (%s), header has %s columns." % (column, len(header)), file=stderr)
                        raise SystemExit
                    columns_to_filter.append(column-1)
                    header_filtered.append(header[column-1])

                except ValueError: # as title
                    if column not in header:
                        print("Error: invalid column ('%s'), not in header: %s." % (column, header), file=stderr)
                        raise SystemExit
                    columns_to_filter.append(header.index(column))
                    header_filtered.append(column)

        # invert columns to filter if cutting only
        if invert and filter_columns_only:
            # get filtered columns
            unfiltered_columns = columns_to_filter
            unfiltered_titles = header_filtered
            # get original columns
            header_filtered = header
            columns_to_filter = []
            for column_number in range(0, len(header)):
                columns_to_filter.append(column_number)
            # invert filter columns
            for column in unfiltered_columns:
                columns_to_filter.remove(column)
            for title in unfiltered_titles:
                header_filtered.remove(title)

        with open(output_name, 'w', newline='', encoding=encoding) as output_file:
            file_writer = writer(output_file, delimiter=delimiter, quoting=quoting, quotechar=quotechar)

            if filter_columns_only:
                file_writer.writerow(header_filtered)
            else: # all columns
                file_writer.writerow(header)

            for line in file_reader:
                index = file_reader.line_num
                print('Read %s lines.' % index, end='\r')\
                if (index/10000).is_integer() else None

                data_to_filter = []

                for column in columns_to_filter:
                    try: # filter line
                        filter_match = False

                        if strings:
                            data_to_filter = line[column]

                            if ignore_cases:
                                data_to_filter = data_to_filter.lower()

                            if whole_words:
                                if (all_words and all(search(r'\b%s\b' % s, data_to_filter) for s in strings))\
                                or (not all_words and any(search(r'\b%s\b' % s, data_to_filter) for s in strings)):
                                    filter_match = True

                            elif (all_words and all(s in data_to_filter for s in strings))\
                            or (not all_words and any(s in data_to_filter for s in strings)):
                                filter_match = True

                        elif any(i for i in [minimum, maximum]):
                            data_to_filter = line[column]

                            if is_number(data_to_filter):
                                data_to_filter = float(data_to_filter)

                            if all(i for i in [minimum, maximum]):
                                if (minimum <= data_to_filter <= maximum):
                                    filter_match = True

                            elif (minimum and minimum <= data_to_filter)\
                            or (maximum and maximum >= data_to_filter):
                                filter_match = True

                        elif filter_columns_only:
                            data_to_filter.append(line[column])

                        if filter_match:
                            break

                    except IndexError:
                        if index_ignore:
                            continue
                        raise

                if filter_columns_only:
                    line = data_to_filter

                if (filter_match and not invert)\
                or (not filter_match and invert)\
                or (filter_columns_only and data_to_filter != []):
                    int_lines_matched += 1
                    file_writer.writerow(line)

    int_header_total = len(header)
    int_header_unmatched = int_header_total - len(header_filtered)
    int_header_matched = int_header_total - int_header_unmatched

    int_lines_total = file_reader.line_num
    int_lines_unmatched = int_lines_total - int_lines_matched

    print('Read', str(int_header_total), 'total columns.\n'+
          str(int_header_unmatched), 'unmatching columns.\n'+
          str(int_header_matched), 'columns after filtering.')\
    \
    if filter_columns_only else\
    \
    print('Read', str(int_lines_total), 'total lines.\n'+
          str(int_lines_unmatched), 'unmatching lines.\n'+
          str(int_lines_matched), 'lines after filtering.')

def date_str_with_time(date_str, default_time='00:00:00'):
    '''
    Returns string in YYYY-MM-DD hh:mm:ss format.
    '''
    if len(date_str) >= 10:
        y = int(date_str[:4])
        y = date_str[:4]
        m = int(date_str[5:7])
        m = date_str[5:7]
        d = int(date_str[8:10])
        d = date_str[8:10]

    # get time from string
    if len(date_str) == 19:
        default_time = date_str[11:]

    # set new date string
    return (str(y)+'-'+str(m)+'-'+str(d)+' '+default_time)

def datetime_to_timestamp(date_time, utc=True):
    '''
    Converts datetime object to timestamp,
    e.g. datetime(2016, 2, 16, 17, 38, 53) => 1455651533.
    '''
    if utc: # universal time coordinates
        return date_time.replace(tzinfo=timezone.utc).timestamp()
    return date_time.timestamp()

def get_file_delimiter(input_name, encoding=ENCODING):
    '''
    Returns character delimiter from file.
    '''
    with open(input_name, 'rt', encoding=encoding) as input_file:
        file_reader = reader(input_file)
        header = str(next(file_reader))

    for i in ['|', '\\t', ';', ',']:
        if i in header: # \\t != \t
            return i.replace('\\t', '\t')

    return '\n'

def is_date(str_):
    '''
    Returns True if input is a date string.
    '''
    try:
        datetime.strptime(str_, '%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            datetime.strptime(str_, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return False
    return True

def is_number(str_):
    '''
    Returns True if the input is an integer or float.
    '''
    try:
        int(str_)
    except Exception:
        try:
            float(str_)
            return True
        except Exception:
            return False
    return True

def load_list(filename):
    '''
    Reads a custom file if present and returns a
    list of the data in it. If no data is in the file,
    or the file is not present, it returns an empty list.
    '''
    filter_strings = set()
    with open(filename, 'rt') as f:
        for line in f:
            filter_strings.add(line.rstrip())
    return list(filter_strings)

if __name__ == "__main__":

    parser = ArgumentParser()

    parser.add_argument('input', action='store', help='input file name')
    parser.add_argument('-o', '--output', action='store', help='output file name')
    parser.add_argument('-s', '--strings', default=[], action='store', help='words or file containing list')
    parser.add_argument('-c', '--columns', default=[], action='store', help='column indexes or titles (comma separated)')
    parser.add_argument('-m', '--minimum', action='store', help='value or date for timestamp (YYYY-MM-DD hh:mm:ss)')
    parser.add_argument('-M', '--maximum', action='store', help='value or date for timestamp (YYYY-MM-DD hh:mm:ss)')
    parser.add_argument('-a', '--all-words', action='store_true', help='match only lines with all strings')
    parser.add_argument('-w', '--whole-words', action='store_true', help='match only lines with whole strings')
    parser.add_argument('-i', '--ignore-cases', action='store_true', help='ignore letter cases such as AaBbCc')
    parser.add_argument('-v', '--invert', action='store_true', help='invert line matching rules')
    parser.add_argument('-d', '--delimiter', action='store', help='column field delimiter')
    parser.add_argument('-q', '--quoting', action='store', type=int, choices=QUOTING.keys(), default=0, help='text quoting %s' % QUOTING)
    parser.add_argument('-e', '--encoding', action='store', help='file encoding (default: %s)' % ENCODING)
    parser.add_argument('--index-ignore', action='store_true', help='skip line and bypass IndexError exceptions')

    args = parser.parse_args()

    filter_csv(args.input,
               args.output,
               args.strings,
               args.columns,
               args.minimum,
               args.maximum,
               args.all_words,
               args.whole_words,
               args.ignore_cases,
               args.invert,
               args.delimiter,
               args.quoting,
               args.encoding,
               args.index_ignore)