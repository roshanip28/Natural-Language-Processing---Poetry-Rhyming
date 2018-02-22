#!/usr/bin/env python
import argparse
import sys
import codecs
if sys.version_info[0] == 2:
  from itertools import izip
else:
  izip = zip
from collections import defaultdict as dd
import re
import os.path
import gzip
import tempfile
import shutil
import atexit

# Use word_tokenize to split raw text into words
from string import punctuation

import nltk
from nltk.tokenize import word_tokenize
from nltk.tokenize import RegexpTokenizer


scriptdir = os.path.dirname(os.path.abspath(__file__))

reader = codecs.getreader('utf8')
writer = codecs.getwriter('utf8')

def prepfile(fh, code):
  if type(fh) is str:
    fh = open(fh, code)
  ret = gzip.open(fh.name, code if code.endswith("t") else code+"t") if fh.name.endswith(".gz") else fh
  if sys.version_info[0] == 2:
    if code.startswith('r'):
      ret = reader(fh)
    elif code.startswith('w'):
      ret = writer(fh)
    else:
      sys.stderr.write("I didn't understand code "+code+"\n")
      sys.exit(1)
  return ret

def addonoffarg(parser, arg, dest=None, default=True, help="TODO"):
  ''' add the switches --arg and --no-arg that set parser.arg to true/false, respectively'''
  group = parser.add_mutually_exclusive_group()
  dest = arg if dest is None else dest
  group.add_argument('--%s' % arg, dest=dest, action='store_true', default=default, help=help)
  group.add_argument('--no-%s' % arg, dest=dest, action='store_false', default=default, help="See --%s" % arg)



class LimerickDetector:

    def __init__(self):
        """
        Initializes the object to have a pronunciation dictionary available
        """
        self._pronunciations = nltk.corpus.cmudict.dict()


    def num_syllables(self, word):
        """
        Returns the number of syllables in a word.  If there's more than one
        pronunciation, take the shorter one.  If there is no entry in the
        dictionary, return 1.
        """
        if word not in self._pronunciations:
            # print "not"
            return 1

        var = self._pronunciations[word]
        # print var
        sum = 0
        num_stress = []
        for i in var:
            for j in i:
                # print j
                if j[-1].isdigit():
                    sum += 1
                    # print sum
            num_stress.append(sum)
            sum = 0
        # print "\n"
        return min(num_stress)

        # TODO: provide an implementation!

    def rhymes(self, a, b):
        """
        Returns True if two words (represented as lower-case strings) rhyme,
        False otherwise.
        """
        word1 = self._pronunciations[a]
        # print word1
        word2 = self._pronunciations[b]
        # print word2
        str1 = ''
        str2 = ''
        s1 = []
        s2 = []
        vowels = 'AEIOU'

        for m in word1:
            if m[0][0] in vowels:
                for h in range(0, len(m)):
                    str1 += m[h]
            else:
                for i in range(0, len(m)):
                    if m[i][0] not in vowels:
                        continue
                    else:
                        for x in range(i, len(m)):
                            str1 += m[x]
                        break
            s1.append(str1)
            str1 = ''
        # print s1


        for m in word2:
            if m[0][0] in vowels:
                for h in range(0, len(m)):
                    str2 += m[h]
            else:
                for i in range(0, len(m)):
                    if m[i][0] not in vowels:
                        continue
                    else:
                        for x in range(i, len(m)):
                            str2 += m[x]
                        break
            s2.append(str2)
            str2 = ''
        # print s2

        for substr1 in s1:
            for substr2 in s2:
                if len(substr1) > len(substr2) and substr1.endswith(substr2):
                    return True
                elif len(substr1) < len(substr2) and substr2.endswith(substr1):
                    return True
                else:
                    if substr1 == substr2:
                        return True
        return False

        # TODO: provide an implementation!



    def apostrophe_tokenize(self,string):
        token_list=string.split()
        return token_list



    def guess_syllables(self,word):
        total=0
        vowels='aeiouy'
        word=word.lower()
        word=word.strip(":;,.!?")
        #print word
        #if no word given or is empty
        if word==None or word=="" or len(word)==0:
            #print 'No word'
            return 0
        #short word with 3 or less letters always have single syllable
        if len(word)<=3:
            return 1
        #if word[-1:] == "y" and word[-2] not in vowels:
        #    total += 1
        if word[len(word)-2] not in vowels and word.endswith('e'):
            total-=1
        if word[len(word)-3] not in vowels and word.endswith('le'):
            total+=1
        if word[len(word)-4] not in vowels and word.endswith('les'):
            total+=1
        if word[0] in vowels:
            total+=1
        for i in range(1,len(word)):
            if word[i] in vowels and word[i-1] not in vowels:
                total+=1
        for i in range(1,len(word)):
            if word[i]=='i' and (word[i+1]=='a' or word[i+1]=='o'):
                total+=1
        if word.endswith('ed'):
            if(word[len(word)-3] !='t' and word[len(word)-3]!='d'):
                total-=1
        if word.endswith('fully') and len(word)!=5:
            total-=1
        if word.endswith('yee'):
            total+=1
        #add one if starts with "mc"
        if word[:2] == "mc":
            total += 1
        #considering words like coexists and preamble
        if (word[:3]=="pre" and word[3] in vowels) or (word[:2]=="co" and word[2] in vowels):
            total+=1

        return total



    def is_limerick(self, text):
        """
        Takes text where lines are separated by newline characters.  Returns
        True if the text is a limerick, False otherwise.

        A limerick is defined as a poem with the form AABBA, where the A lines
        rhyme with each other, the B lines rhyme with each other, and the A lines do not
        rhyme with the B lines.


        Additionally, the following syllable constraints should be observed:
          * No two A lines should differ in their number of syllables by more than two.
          * The B lines should differ in their number of syllables by no more than two.
          * Each of the B lines should have fewer syllables than each of the A lines.
          * No line should have fewer than 4 syllables

        (English professors may disagree with this definition, but that's what
        we're using here.)


        """

        last_words = []
        last_words_A = []
        last_words_B = []
        a_line = []
        b_line = []
        texta = text.strip().split("\n")
        for line in texta:
            newline = re.sub(r"[^\w\s']", '', line)
            new = word_tokenize(newline)
            last_words.append(new[len(new) - 1])
        for y in range(0, len(last_words)):
            if y < 2 or y == 4:
                last_words_A.append(last_words[y])
            elif y > 1 and y < 4:
                last_words_B.append(last_words[y])
        if len(last_words) != 5:
            # print "false1"
            return False
        # print type(newline)
        # print last_words
        # print last_words_A
        # print last_words_B

        for i in range(0, len(last_words_A) - 1):
            if self.rhymes(last_words_A[i], last_words_A[i + 1]) == True:
                continue
            else:
                # print "false2"
                return False

        for i in range(0, len(last_words_B) - 1):
            if self.rhymes(last_words_B[i], last_words_B[i + 1]) == True:
                continue
            else:
                # print "false3"
                return False

        for i in range(0, len(last_words_A)):
            for j in range(0, len(last_words_B)):
                if self.rhymes(last_words_A[i], last_words_B[j]) == True:
                    return False

        count_syll = 0
        count_syl = []
        while ' ' in texta:
            texta.remove(' ')

        for lines in texta:
            newline = re.sub(r"[^\w\s']", '', lines)
            #print newline
            new = word_tokenize(newline)
            # x=lines.split(' ')
            for f in new:
                count_syll += self.num_syllables(f)
            count_syl.append(count_syll)
            count_syll = 0

        a_line.append(count_syl[0])
        a_line.append(count_syl[1])
        a_line.append(count_syl[4])
        b_line.append(count_syl[2])
        b_line.append(count_syl[3])
        for i in a_line:
            for j in b_line:
                if i > j:
                    continue
                else:
                    # print "false4"
                    return False

        # print a_line
        # print b_line
        # print count_syl

        for i in range(0, len(a_line) - 1):
            if abs(a_line[i + 1] - a_line[i]) < 3:
                continue
            else:
                # print "false4"
                return False

        for i in range(0, len(b_line) - 1):
            if abs(b_line[i + 1] - b_line[i]) < 3:
                continue
            else:
                # print "false5"
                return False

        for t in count_syl:
            if t >= 4:
                continue
            else:
                # print "false6"
                return False

        # print type(a_line)

        # TODO: provide an implementation!
        return True



# The code below should not need to be modified
def main():
  parser = argparse.ArgumentParser(description="limerick detector. Given a file containing a poem, indicate whether that poem is a limerick or not",
                                   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  addonoffarg(parser, 'debug', help="debug mode", default=False)
  parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
  parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")




  try:
    args = parser.parse_args()
  except IOError as msg:
    parser.error(str(msg))

  infile = prepfile(args.infile, 'r')
  outfile = prepfile(args.outfile, 'w')

  ld = LimerickDetector()
  lines = ''.join(infile.readlines())
  outfile.write("{}\n-----------\n{}\n".format(lines.strip(), ld.is_limerick(lines)))

if __name__ == '__main__':
  main()
