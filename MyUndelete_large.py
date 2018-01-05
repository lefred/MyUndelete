#!/usr/bin/python

#
# MyUndelete.py - MySQL undelete from ROW base binary logs
#
# Author : Frederic -lefred- Descamps <lefred@lefred.be>
# Version: 0.3
# Date   : 2018-01-05
#
# Use with care
#
# License: GPLv2 (c) Frederic Descamps


import os
import base64
import sys, getopt
import subprocess
import tempfile
import re
from distutils.util import strtobool

debug  = False
debug2 = False

def main(argv):
   binlog = ''
   startpos = ''
   endpos = ''
   check_insert = False
   check_update = False
   global debug
   global debug2
   try:
      opts, args = getopt.getopt(argv,"hb:dDe:is:u",["binlog=","debug","debug2","end=","insert","start=","update"])
   except getopt.GetoptError:
      print 'MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i] [-u] [-d]'
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
         print '  -d | --debug    : add debug messages'
         print '  -D | --debug2   : add debug messages related to records content'
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
      elif opt in ("-d", "--debug"):
         debug = True
      elif opt in ("-D", "--debug2"):
         debug2 = True

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

def findnth(haystack, needle, n):
    parts= haystack.split(needle, n+1)
    if len(parts)<=n+1:
        return -1
    return len(haystack)-len(parts[-1])-len(needle)

def p_debug(msg):
    global debug
    if debug: print "DEBUG: " + msg

def p_debug2(msg):
    global debug2
    if debug2: print "DEBUG REC: " + msg

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
        decodedline = base64.b64decode(base64line)
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
      if event_type: p_debug("event_type = %s -> %s" % (repr(event_type), ord(event_type)))
      if event_type and ord(event_type) == 25 :
         found_del = True
         p_debug("ROW event : %s" % base64line)
         print "Event type (%s) is a delete v1" % repr(event_type)
         new_header[4] = chr(23) #\x17
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif event_type and ord(event_type) == 32:
         found_del = True
         p_debug("ROW event : %s" % base64line)
         print "Event type (%s) is a delete v2" % repr(event_type)
         new_header[4] = chr(30) #\x1e
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
         old_encodedheader = base64.b64encode(old_header)[:-2]
      elif event_type and ord(event_type) == 23:
         found_del = True
         p_debug("ROW event : %s" % base64line)
         print "Event type (%s) is an insert v1" % repr(event_type)
         new_header[4] = chr(25) #\x19
         new_encodedheader = base64.b64encode(''.join(new_header[:8]))[:-2]
         old_encodedheader = base64.b64encode(old_header[:8])[:-2]
      elif event_type and ord(event_type) == 30 and check_insert:
         found_del = True
         p_debug("ROW event : %s" % base64line)
         print "Event type (%s) is an insert v2" % repr(event_type)
         new_header[4] = chr(32) #\x25
         new_encodedheader = base64.b64encode(''.join(new_header))[:-2]
         old_encodedheader = base64.b64encode(old_header)[:-2]
      elif event_type and ord(event_type) == 31 and check_update:
         found_update = True
         p_debug("ROW event : %s" % base64line)
         print "Event type (%s) is an update v2" % repr(event_type)
         binlog_event.append(base64line)

      if found_del:
         p_debug("Old header = %s" % old_encodedheader)
         p_debug("New header = %s" % new_encodedheader)
         if user_yes_no_query("Ready to revert the statement ?"):
            c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
            p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)
 
            c2 = ['sed', "s/^%s/%s/" % (old_encodedheader, new_encodedheader)]
            p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE)
             
            c3 = ['/usr/bin/sudo', '/bin/sed', "s/GTID_NEXT= '........-....-....-....-............*$/GTID_NEXT= 'AUTOMATIC';/"]
            p3 = subprocess.Popen(c3, stdin=p2.stdout, stdout=subprocess.PIPE)

            c4 = ['mysql']
            p4 = subprocess.Popen(c4, stdin=p3.stdout)
  
	    p1.wait()
	    p2.wait()
	    p3.wait()
	    p4.wait()
             
            print "Done... I hope it worked ;)"
            sys.exit(0) 
         else:
            print "Bye...bye... my data"
  if found_update:
      print "We got an update!!"
      # let's  consider that the PK is always on one binlog line
      # check that we have currently the right binlog line 
      if base64.b64decode(binlog_event[0])[31] != "\xff":
          print "ERROR: problem parsing binary log header"
          sys.exit(5)
      # find the "marker" and the PK
      to_find = base64.b64decode(binlog_event[0])[32]
      p_debug("to_find = %s (%s)" % (repr(to_find), ord(to_find)))
 
      # let's concatenate to create the full binlog
      binlog_event_str = "".join(binlog_event)
      #binlog_event_str_dec = base64.b64decode(binlog_event_str)
      f_bin = tempfile.NamedTemporaryFile(delete=False) 
      f_bin.write(binlog_event_str)
      f_bin.close()
      #with open('/tmp/MyUndelete_dec', 'w+') as outfile:
      f_bin_new_un = tempfile.NamedTemporaryFile(delete=False)
      p_base = subprocess.Popen(["/bin/base64","-d",f_bin.name], stdout=f_bin_new_un)
      p_base.communicate()
      f_bin_new_un.close()
      with open(f_bin_new_un.name, 'rb') as infile:
         binlog_event_str_dec = infile.read() 
      infile.close()
      p_debug2("binlog_event = %s" % binlog_event_str)
      p_debug2("binlog_event_dec = %s" % repr(binlog_event_str_dec))

      # find all occurence of to_find[0] so the byte at [32] to find how may records
      # are in the event, then for each of them we need to recreate everything
      total_records_in_event = int(binlog_event_str_dec.count(to_find)) / 2
      print "Total occurence of records =  %s" % total_records_in_event
      new_binlog_event_str_dec =  binlog_event_str_dec[0:32]
      # TODO: loop on each records to rebuild them      
      for i_rec in range(0, total_records_in_event):
          p_debug("rebuilding record %s of %s" % (i_rec, total_records_in_event))
          old_record_pos = findnth(binlog_event_str_dec, to_find, i_rec * 2)
          new_record_pos = findnth(binlog_event_str_dec, to_find, (i_rec * 2) + 1) 
          new_record_end_pos = findnth(binlog_event_str_dec, to_find, (i_rec * 2) + 2) 
          p_debug2("old %s record starts at %s and finishes at %s" % (i_rec, old_record_pos, new_record_pos))
          p_debug2("new %s record starts at %s and finishes at %s" % (i_rec, new_record_pos, new_record_end_pos))
          if new_record_end_pos == -1: new_record_end_pos = -4
          old_image = binlog_event_str_dec[old_record_pos:new_record_pos]
          new_image = binlog_event_str_dec[new_record_pos:new_record_end_pos]
          p_debug2("old record = %s" % repr(old_image))
          p_debug2("new record = %s" % repr(new_image))
          new_binlog_event_str_dec = new_binlog_event_str_dec + new_image + old_image
      new_binlog_event_str_dec = new_binlog_event_str_dec + binlog_event_str_dec[-4:]
      new_binlog_envent_str_enc = base64.b64encode(new_binlog_event_str_dec)
      p_debug2("new ROW DEC = %s" % repr(new_binlog_event_str_dec)) 
      p_debug2("new ROW ENC = %s" % new_binlog_envent_str_enc)
      n = 76
      new_binlog_list = [new_binlog_envent_str_enc[i:i+n] for i in range(0, len(new_binlog_envent_str_enc), n)]
      
      f_old = tempfile.NamedTemporaryFile(delete=False) 
      for i in binlog_event:
      	  f_old.write(re.escape(i) + "\n")
      f_old.close()
      f_new = tempfile.NamedTemporaryFile(delete=False)
      for binlog_line  in new_binlog_list:
          f_new.write(re.escape(binlog_line) + "\n")
      f_new.close()

      if user_yes_no_query("Ready to revert the statement ?"):
          c1 = ['/usr/bin/sudo', '/usr/bin/mysqlbinlog', '--start-position=%s' % startpos, '--stop-position=%s' % endpos, binlog]
          p1 = subprocess.Popen(c1, stdout=subprocess.PIPE)

          c2 = ['/usr/bin/sudo', '/usr/bin/awk', 'BEGIN{ RS=\"\" } FILENAME==ARGV[1] { s=$0 } FILENAME==ARGV[2] { r=$0 } FILENAME==ARGV[3] { sub(s,r) ; print }',
                f_old.name, f_new.name, "-"]  
          p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE)
          
          c3 = ['/usr/bin/sudo', '/bin/sed', "s/GTID_NEXT= '........-....-....-....-............*$/GTID_NEXT= 'AUTOMATIC';/"]
          p3 = subprocess.Popen(c3, stdin=p2.stdout, stdout=subprocess.PIPE)

          c4 = ['mysql']
          p4 = subprocess.Popen(c4, stdin=p3.stdout)
          print "Sending to mysql..."
          p1.wait()
          p2.wait()
          p3.wait()
          p4.wait()

          os.unlink(f_old.name)
          os.unlink(f_new.name)
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

