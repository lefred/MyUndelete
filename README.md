MyUndelete
==========

Undelete deleted rows from MySQL ROW binary logs

MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i] [-u]

  -b | --binlog=  : path of the binary log file
  -s | --start=   : start position
  -e | --end=     : stop position
  -i | --insert   : consider also INSERT statements (by default, only DELETE)
  -u | --update   : consider also UPDATE statements (by default, only DELETE)
  -d | --debug    : add debug messages

Info: The program expects that you have read access to the binary log
and you have all eventual MySQL credential in ~/.my.cnf

Examples
========

$ sudo ./MyUndelete.py -s 41989 -e 42207 -i -b /var/lib/mysql/mysqld-bin.000004

*** WARNING *** USE WITH CARE ****

Binlog file is  /var/lib/mysql/mysqld-bin.000004
Start Position file is  41989
End Postision file is  42207
We also look to undo INSERTs
Event type ('\x1e') is an insert v2
Ready to revert the statement ? [y/n]
y
Done... I hope it worked ;)

