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
import re
from distutils.util import strtobool

def main(argv):
   binlog = ''
   startpos = ''
   endpos = ''
   check_insert = False
   check_update = False
   try:
      opts, args = getopt.getopt(argv,"hb:e:is:u",["binlog=","end=","insert","start=","update"])
   except getopt.GetoptError:
      print 'MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i] [-u]'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i] [-u]'
         print ''
         print '  -b | --binlog=  : path of the binary log file'
         print '  -s | --start=   : start position'
         print '  -e | --end=     : stop position'
         print '  -i | --insert   : consider also INSERT statements (by default, only DELETE)'
         print '  -u | --update   : consider also UPDATE statements (by default, only DELETE)'
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
      elif opt in ("-u", "--update"):
         check_update = True

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
   return(binlog, startpos, endpos, check_insert, check_update)

def user_yes_no_query(question):
    sys.stdout.write('%s [y/n]\n' % question)
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            sys.stdout.write('Please respond with \'y\' or \'n\'.\n')


def mysqlbinlog(binlog, startpos, endpos, check_insert, check_update):

  if check_insert:
      print "We also look to undo INSERTs"
  #import pdb; pdb.set_trace()
  c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
  p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
 
  #c2 = ['awk', 'c&&!--c;/^BINLOG /{c=2}']
  c2 = ['awk', '/\/*!*\/\;/{flag=0}flag;/^BINLOG /{flag=1}']
  p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE)
 
  found_del = False 
  found_update = False 
  get_full_binlog = False 
  binlog_event = []
  for line in iter(p2.stdout.readline, b''):
      base64line = line.rstrip()
      try:
        decodedline= base64.b64decode(base64line)
      except:
        print "ERROR: no valid event found !"
        sys.exit(4) 
      if found_update:
        binlog_event.append(base64line)
        continue  
      old_header = decodedline[:10]
      new_header = list(old_header)
      try:
        event_type = old_header[4]
      except:
         event_type = '' 
      print "DEBUG: event_type = %s" % repr(event_type)
      if ord(event_type) == 25:
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is a delete v1" % repr(event_type)
         new_header[4] = chr(23) #\x17
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif ord(event_type) == 32:
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is a delete v2" % repr(event_type)
         new_header[4] = chr(30) #\x1e
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
      elif ord(event_type) == 23:
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is an insert v1" % repr(event_type)
         new_header[4] = chr(25) #\x19
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif ord(event_type) == 30 and check_insert:
         found_del = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is an insert v2" % repr(event_type)
         new_header[4] = chr('32') #\x25
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
         old_encodedheader = base64.b64encode(old_header)[:-2]
      elif ord(event_type) == 31 and check_update:
         found_update = True
         print "ROW event : %s" % base64line
         print "Event type (%s) is an update v2" % repr(event_type)
         binlog_event.append(base64line)

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
  if found_update:
      print "We got an update!!"
      for i in binlog_event[:-1]:
          print "Binlog line : %s" % i
      for i in binlog_event[:-1]:
          print "Binlog line decoded : %s" % repr(base64.b64decode(i))
      # let's  consider that the PK is always on one binlog line
      # check that we have currently the right binlog line 
      if base64.b64decode(binlog_event[0])[31] != "\xff":
          print "ERROR: problem parsing binary log header"
          sys.exit(5)
      # find the "marker" and the PK
      to_find = base64.b64decode(binlog_event[0])[32] + base64.b64decode(binlog_event[0])[33]
      got_it_in = -1
      old_image = [None]*(len(binlog_event))
      new_image = [None]*(len(binlog_event))
      old_queue = [None]*(len(binlog_event))
      got_position = False
      position = False
      old_header = False
      for binlog_line in binlog_event:
          got_it_in += 1
          position = base64.b64decode(binlog_line).rfind(to_find)
          print "Position = %d in line %d" % (position, got_it_in)
          print "DEBUG : lenght of the event: %s" % len(binlog_line)
          if not old_header:
             old_header = base64.b64decode(binlog_line)[:32]
          if got_it_in == (len(binlog_event)-2) and (len(binlog_event[got_it_in+1])<4):
	      print "DEBUG: we are in the 2nd last binlog line"
              take_x_bytes = 4 - len(binlog_event[got_it_in+1])
              old_queue[got_it_in] = base64.b64decode(binlog_line)[-take_x_bytes:]
              print "DEBUG: old_queue = %s" % repr(old_queue[got_it_in])
          elif got_it_in == (len(binlog_event)-1):
              # we need to keep the queue
              print "DEBUG: we are in the last binlog line"
              old_queue[got_it_in]  = base64.b64decode(binlog_line)[-4:]
              print "DEBUG: old_queue = %s" % repr(old_queue[got_it_in])
              if len(binlog_line) == 4:
                old_image[got_it_in] = ""  
                new_image[got_it_in] = ""  
              continue
          else:
	      old_queue[got_it_in] = "" 
          if not position and not got_position:
              old_image[got_it_in] = base64.b64decode(binlog_line)
              continue
          elif position == 32 and got_it_in == 0:
              # we need to find it on another line
              old_header = base64.b64decode(binlog_line)[:32]
              old_image[got_it_in] = base64.b64decode(binlog_line)[32:]
              continue
          else:              
            if position:
                got_position = True
            if got_it_in == 0:
                # now we need to retrieve the value from 32 to the position
                # as the new value is also on the first line
                print "DEBUG binlog_line : %s" % repr(binlog_line)
                old_image[got_it_in]=base64.b64decode(binlog_line)[32:position]
                print "DEBUG old_image : %s" % (old_image)
            else:
                old_image[got_it_in]=base64.b64decode(binlog_line)[:position]

            if got_it_in == (len(binlog_event)-2) and position:
              new_image[got_it_in]=base64.b64decode(binlog_line)[position:-2]
            elif got_it_in == (len(binlog_event)-2):
              new_image[got_it_in]=base64.b64decode(binlog_line)[:-2]
            elif position and len(binlog_event) == 1:
              new_image[got_it_in]=base64.b64decode(binlog_line)[position:-4]
            elif position: 
              new_image[got_it_in]=base64.b64decode(binlog_line)[position:]
            else:
              new_image[got_it_in]=base64.b64decode(binlog_line)

      replacement = []
      original = []
      # we need to rebuild the binary log event
      print "DEBUG: %s" % len(binlog_event)
      for i in range(len(binlog_event)):
          print "   EVENT (%s) : %s" % (i, repr(base64.b64decode(binlog_event[i])))
          print "   EVENT (%s) : %s" % (i, binlog_event[i])
          print "   old_header : %s (%s)" % (repr(old_header), base64.b64encode(old_header))
          print "   old_image  : %s (%s)" % (repr(old_image[i]), base64.b64encode(old_image[i]))
          print "   new_image  : %s (%s)" % (repr(new_image[i]), base64.b64encode(new_image[i]))
          print "   old_queue  : %s (%s)" % (repr(old_queue[i]), base64.b64encode(old_queue[i]))
          str = ""
          if i == 0:
             str = old_header + new_image[i]
          elif new_image[i]: 
             str = str + new_image[i]
          if old_image[i]:
             str = str + old_image[i]
          if old_queue[i]:
             str = str + old_queue[i]
          #replacement.append(base64.b64encode(str))
          #original.append(binlog_event[i])
          print "  new : %s" % repr(str)
          replacement.append(re.escape(base64.b64encode(str)).replace('\\+','+'))
          original.append(re.escape(binlog_event[i]).replace('\\+','+'))
	  
      print "OLD : " 
      print  original
      print "NEW : " 
      print replacement
      if user_yes_no_query("Ready to revert the statement ?"):
          c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
          p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
          
          tab_proc = {}
          tab_cmd = {}
          k = 0
          for event in original:
          	tab_cmd[k]  = ['sed', "s/^%s/%s/" % (original[0], replacement[0])]
                if k == 0:
          	   tab_proc[k] = subprocess.Popen(tab_cmd[k], stdin=p1.stdout, stdout=subprocess.PIPE)
                else:
          	   tab_proc[k] = subprocess.Popen(tab_cmd[k], stdin=tab_proc[k-1].stdout, stdout=subprocess.PIPE)
         
          c3 = ['mysql']
          p3 = subprocess.Popen(c3, stdin=tab_proc[k].stdout, stdout=subprocess.PIPE)
         
          print "Done... I hope it worked ;)"
          sys.exit(0) 
      else:
          print "Bye...bye... my data"

  elif not found_del:
      print "Nothing to do..."
        
        

if __name__ == "__main__":
   print ""
   print "*** WARNING *** USE WITH CARE ****"
   print ""
   (binlog, startpos, endpos, check_insert, check_update)=main(sys.argv[1:])
   mysqlbinlog(binlog, startpos, endpos, check_insert, check_update)

