py_filter_csv
---

Filter CSV lines and columns for words or numerical interval.

Allows automatic minimum and maximum date conversion to timestamp.

Tested by comparing output results with GNU `grep`.

```
usage: filter_csv.py [-h] [-o OUTPUT] [-s STRINGS] [-c COLUMNS] [-m MINIMUM]
                     [-M MAXIMUM] [-a] [-w] [-i] [-v]
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
                        input column names
  -m MINIMUM, --minimum MINIMUM
                        value or date for timestamp (YYYY-MM-DD hh:mm:ss)
  -M MAXIMUM, --maximum MAXIMUM
                        value or date for timestamp (YYYY-MM-DD hh:mm:ss)
  -a, --all-words       match only lines with all strings
  -w, --whole-words     match only lines with whole strings
  -i, --ignore-cases    ignore letter cases such as AaBbCc
  -v, --invert          invert line matching rules
```