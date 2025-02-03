# Copyright 2025 Craig Wright
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
from collections import namedtuple
import sys

def col_to_index(col_name):
  """
  :param col_name: column in the CSV as displayed by Sheets
  :returns: zero offset index into CSV row
  """
  col_name = col_name.upper()
  a_value = ord('A')
  z_value = ord('Z')
  val = 0
  for i, c in enumerate(reversed(col_name)):
    char_val = ord(c)
    assert(char_val >= a_value and char_val <= z_value)
    digit =  (char_val-a_value+1)
    val +=  digit * (26**i)
  return val-1

ROW_INDEX_SURVEY_TYPE = col_to_index('K')

# Answers for a single division of the school for a particular
# division of the school
DIVISION_DATA_ARGS =  ("eduction", "growth",
  "virtues", "character_growth",
  "teacher_communication", "leadership_communication",
  "welcoming",
  "strengths", "weaknesses")
DIVISION_ARG_COUNT = len(DIVISION_DATA_ARGS)
DivisionAnswers = namedtuple(
  "DivisionAnswers",
  [
    "division_name",
    *DIVISION_DATA_ARGS
  ]
)

WHOLE_SCHOOL_ARGS = ("strengths", "weaknesses", "tenure", "iep_etc", "minority")
WHOLE_SCHOOL_ARG_COUNT = len(WHOLE_SCHOOL_ARGS)
WholeSchoolAnswers = namedtuple(
  "WholeSchoolAnswers",
  WHOLE_SCHOOL_ARGS
)

GRAMMAR = "grammar"
MIDDLE = "middle"
HIGH = "high"
DIVISION_TO_INDEX = {GRAMMAR: 0, MIDDLE : 1, HIGH : 2}

class SingleDivisionReader:
  def __init__(self, division, start, end, strengths, weaknesses, whole_school_cols):
    self.division = division
    self.start = col_to_index(start)
    self.end = col_to_index(end)
    self.strengths = col_to_index(strengths)
    self.weaknesses = col_to_index(weaknesses)
    self.whole_school_cols = [col_to_index(x) for x in whole_school_cols]

  def __call__(self, row):
    division_args = [self.division]
    whole_args = []
    for col in range(self.start, self.end+1):
      if col not in self.whole_school_cols:
        division_args.append(row[col])
    division_args.append(row[self.strengths])
    division_args.append(row[self.weaknesses])
    for col in self.whole_school_cols:
      whole_args.append(row[col])

    out = [None, None, None, WholeSchoolAnswers(*whole_args)]
    for k,v in DIVISION_TO_INDEX.items():
      if k == self.division:
        out[v] = DivisionAnswers(*division_args)
      else:
        out[v] = DivisionAnswers(*[""]*(DIVISION_ARG_COUNT+1))
    return tuple(out)

class MultiDivisionReader:
  def __init__(self, divisions, start_categorical, end_categorical, start_open, end_open, whole_school_cols):
    self.divisions = divisions
    self.start_categorical = col_to_index(start_categorical)
    self.end_categorical = col_to_index(end_categorical)
    self.start_open = col_to_index(start_open)
    self.end_open = col_to_index(end_open)
    self.whole_school_cols = [col_to_index(x) for x in whole_school_cols]

  def __call__(self, row):
    division_args = []
    for d in self.divisions:
      division_args.append([d])

    j = 0
    for i in range(self.start_categorical, self.end_categorical+1):
      division_args[j%len(division_args)].append(row[i])
      j+=1

    args = division_args[:]
    args.append([])
    j = 0
    for i in range(self.start_open, self.end_open+1):
      args[j%len(args)].append(row[i])
      j+=1

    whole_args = args[-1]
    for col in self.whole_school_cols:
      whole_args.append(row[col])

    division_args = args[0:-1]
    out = [None, None, None, WholeSchoolAnswers(*whole_args)]
    for k,v in DIVISION_TO_INDEX.items():
      if k in self.divisions:
        for d in division_args:
          if k == d[0]:
            out[v] = DivisionAnswers(*d)
      else:
        out[v] = DivisionAnswers(*[""]*(DIVISION_ARG_COUNT+1))
    return tuple(out)

SurveyReader = namedtuple(
  'SurveyOffset',
 ['survey_type', 'reader'])

SURVEY_READERS = {
  x.survey_type : x for x in [
    SurveyReader('Grammar School only (K-6)',
                 SingleDivisionReader(GRAMMAR, 'L', 'R', 'S', 'U', ['T', 'V', 'ED', 'EE', 'EF'])),
    SurveyReader('Middle School only (7-8)',
                 SingleDivisionReader(MIDDLE, 'CN', 'CT', 'CU', 'CW', ['CV', 'CX', 'ED', 'EE', 'EF'])),
    SurveyReader('High School only (9-12)',
                 SingleDivisionReader(HIGH, 'DS', 'DY', 'DZ', 'EB', ['EA', 'EC', 'ED', 'EE', 'EF'])),
    SurveyReader('Grammar and Middle School only (K-6 and 7-8)',
                 MultiDivisionReader([GRAMMAR, MIDDLE], 'W', 'AJ', 'AK', 'AP', ['ED', 'EE', 'EF'])),
    SurveyReader('Grammar and High School only (K-6 and 9-12)',
                 MultiDivisionReader([GRAMMAR, HIGH], 'AQ','BD', 'BE', 'BJ', ['ED', 'EE', 'EF'])),
    SurveyReader('Grammar, Middle, and High School (K-6, 7-8, and 9-12)',
                 MultiDivisionReader([GRAMMAR, MIDDLE, HIGH], 'BK', 'CE', 'CF', 'CM', ['ED', 'EE', 'EF'])),
    SurveyReader('Middle and High School only (7-8 and 9-12)',
                 MultiDivisionReader([MIDDLE, HIGH], 'CY', 'DL', 'DM', 'DR', ['ED', 'EE', 'EF']))
  ]}

class Cleaner:
  def __init__(self, filepath):
    with open('out.csv', 'w', newline='') as outfile:
      with open(filepath, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for i, row in enumerate(reader):
          print(f"Processing row {i}")
          # skip two header rows
          if i == 0:
            writer.writerow(Cleaner.make_first_row(row))
          elif i == 1:
            writer.writerow(Cleaner.make_second_row(row))
          else:
            survey_type = row[ROW_INDEX_SURVEY_TYPE]
            reader = SURVEY_READERS[survey_type].reader
            processed_row = reader(row)

            output_row = row[0:col_to_index('K')+1]

            for answers in processed_row[0:3]:
              for attr in DIVISION_DATA_ARGS:
                output_row.append(getattr(answers, attr))

            for attr in WHOLE_SCHOOL_ARGS:
              output_row.append(getattr(processed_row[3], attr))

            writer.writerow(output_row)

  @staticmethod
  def make_first_row(row):
    out = row[0:col_to_index('K')+1]
    out.extend(["grammar"] * DIVISION_ARG_COUNT)
    out.extend(["middle"] * DIVISION_ARG_COUNT)
    out.extend(["high"] * DIVISION_ARG_COUNT)
    out.extend(["whole"] * WHOLE_SCHOOL_ARG_COUNT)
    return out

  @staticmethod
  def make_second_row(row):
    out = row[0:col_to_index('K')+1]
    out.extend(DIVISION_DATA_ARGS)
    out.extend(DIVISION_DATA_ARGS)
    out.extend(DIVISION_DATA_ARGS)
    out.extend(WHOLE_SCHOOL_ARGS)
    return out

if __name__ == "__main__":
  # TODO(@kungfucraig): Do better arg parsing
  filepath = sys.argv[1]
  print("Reading file:", filepath)
  cleaner = Cleaner(filepath)
