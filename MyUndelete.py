#!/usr/bin/python

#
# MyUndelete.py - MySQL undelete from ROW base binary logs
#
# Author : Frederic -lefred- Descamps <lefred@lefred.be>
# Version: 0.1
# Date   : 2014-11-19
#
# Use with care
#
# License: GPLv2 (c) Frederic Descamps

import base64
import sys, getopt
import subprocess
from distutils.util import strtobool

def main(argv):
   binlog = ''
   startpos = ''
   endpos = ''
   check_insert = False
   try:
      opts, args = getopt.getopt(argv,"hb:e:is:",["binlog=","end=","insert","start="])
   except getopt.GetoptError:
      print 'MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i]'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i]'
         print ''
         print '  -b | --binlog=  : path of the binary log file'
         print '  -s | --start=   : start position'
         print '  -e | --end=     : stop position'
         print '  -i | --insert   : consider also INSERT statements (by default, only DELETE)'
         print ''
         print 'Info: The program expects that you have read access to the binary log'
         print 'and you have all eventual MySQL credential in ~/.my.cnf'
         print ''
         sys.exit()
      elif opt in ("-b", "--binlog"):
         binlog = arg
      elif opt in ("-s", "--start"):
         startpos = arg
      elif opt in ("-e", "--end"):
         endpos = arg
      elif opt in ("-i", "--insert"):
         check_insert = True

   if binlog == '':
       print "ERROR: binlog file is required !"
       sys.exit(1)
   if startpos == '':
       print "ERROR: start position is required !"
       sys.exit(2)
   if endpos == '':
       print "ERROR: end position is required !"
       sys.exit(3)
   print 'Binlog file is ', binlog
   print 'Start Position file is ', startpos
   print 'End Postision file is ', endpos 
   return(binlog, startpos, endpos, check_insert)

def user_yes_no_query(question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')


def mysqlbinlog(binlog, startpos, endpos, check_insert):

  if check_insert:
      print "We also look to undo INSERTs"
  #import pdb; pdb.set_trace()
  c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
  p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
 
  c2 = ['awk', 'c&&!--c;/^BINLOG /{c=2}']
  p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE)
 
  found_del = False 
  for line in iter(p2.stdout.readline, b''):
      base64line = line.rstrip()
      try:
        decodedline= base64.b64decode(base64line)
      except:
        print "ERROR: no valid event found !"
        sys.exit(4) 
      old_header = decodedline[:10]
      new_header = list(old_header)
      event_type = old_header[4]
      if event_type == '\x19':
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is a delete v1" % repr(event_type)
         new_header[4] = '\x17'
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif event_type == ' ':
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is a delete v2" % repr(event_type)
         new_header[4] = '\x1e'
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
      elif event_type == '\x17':
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is an insert v1" % repr(event_type)
         new_header[4] = '\x19'
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif event_type == '\x1e' and check_insert:
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is an insert v2" % repr(event_type)
         new_header[4] = ' '
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
         old_encodedheader = base64.b64encode(old_header)[:-2]

      if found_del:
         print "Old header = %s" % old_encodedheader
         print "New header = %s" % new_encodedheader
         if user_yes_no_query("Ready to revert the statement ?"):
            c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
            p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
 
            c2 = ['sed', "s/^%s/%s/" % (old_encodedheader, new_encodedheader)]
            p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE)
             
            c3 = ['mysql']
            p3 = subprocess.Popen(c3, stdin=p2.stdout, stdout=subprocess.PIPE)
             
            print "Done... I hope it worked ;)"
            sys.exit(0) 
         else:
            print "Bye...bye... my data"
  if not found_del:
         print "Nothing to do..."
        
        

if __name__ == "__main__":
   print ""
   print "*** WARNING *** USE WITH CARE ****"
   print ""
   (binlog, startpos, endpos, check_insert)=main(sys.argv[1:])
   mysqlbinlog(binlog, startpos, endpos, check_insert)

