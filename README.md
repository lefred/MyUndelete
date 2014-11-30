[![Stories in Ready](https://badge.waffle.io/lefred/MyUndelete.png?label=ready&title=Ready)](https://waffle.io/lefred/MyUndelete)
# MyUndelete


Undelete deleted rows, delete inserted rows, revert updates from MySQL ROW binary logs.

This is still alpha, certainly the un-update part that has been tested with only v2 ROW events.

## History


After the nice blog post of Scott Noyes (http://thenoyes.com/littlenoise/?p=307), I decided to dig a bit more on the topic of undelete rows from the binary log.

This script allows to undelete records from the BINARY LOG in ROW FORMAT but also revert INSERTs and UPDATEs.

## Syntax

```
MyUndelete.py -b <binlog> -s <start position> -e <end position> [-i] [-u]

  -b | --binlog=  : path of the binary log file
  -s | --start=   : start position
  -e | --end=     : stop position
  -i | --insert   : consider also INSERT statements (by default, only DELETE)
  -u | --update   : consider also UPDATE statements (by default, only DELETE)
  -d | --debug    : add debug messages

Info: The program expects that you have read access to the binary log
and you have all eventual MySQL credential in ~/.my.cnf
```

## Example

### Un-insert


Delete an insert that happened in binary log mysqld-bin.000004 between positon 41989 and 42207.

```
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
```

### Un-update


Let's modify some records and then revert the changes:

```
mysql> select * from fred;
+----+------------+
| id | name       |
+----+------------+
|  1 | Fred       |
|  2 | Jen        |
|  3 | Wilhelmine |
|  4 | Héloïse    |
|  5 | Suhi       |
+----+------------+
mysql> update fred set name = concat(name, "2") where id >3;
Query OK, 2 rows affected (0.03 sec)
Rows matched: 2  Changed: 2  Warnings: 0
mysql> select * from fred;
+----+------------+
| id | name       |
+----+------------+
|  1 | Fred       |
|  2 | Jen        |
|  3 | Wilhelmine |
|  4 | Héloïse2   |
|  5 | Suhi2      |
+----+------------+
5 rows in set (0.00 sec)

mysql> show master status;
+------------------+----------+--------------+------------------+-------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB | Executed_Gtid_Set |
+------------------+----------+--------------+------------------+-------------------+
| mysql-bin.000008 |      357 |              |                  |                   |
+------------------+----------+--------------+------------------+-------------------+
mysql> show binlog events in 'mysql-bin.000008';
+------------------+-----+-------------+-----------+-------------+---------------------------------------+
| Log_name         | Pos | Event_type  | Server_id | End_log_pos | Info                                  |
+------------------+-----+-------------+-----------+-------------+---------------------------------------+
| mysql-bin.000008 |   4 | Format_desc |         1 |         120 | Server ver: 5.6.21-log, Binlog ver: 4 |
| mysql-bin.000008 | 120 | Query       |         1 |         192 | BEGIN                                 |
| mysql-bin.000008 | 192 | Table_map   |         1 |         242 | table_id: 72 (fred.fred)              |
| mysql-bin.000008 | 242 | Update_rows |         1 |         326 | table_id: 72 flags: STMT_END_F        |
| mysql-bin.000008 | 326 | Xid         |         1 |         357 | COMMIT /* xid=22 */                   |
+------------------+-----+-------------+-----------+-------------+---------------------------------------+
5 rows in set (0.00 sec)

$ sudo ./MyUndelete.py  -b /var/lib/mysql/mysql-bin.000008 -s 120 -e 357 -u

*** WARNING *** USE WITH CARE ****

Binlog file is  /var/lib/mysql/mysql-bin.000008
Start Position file is  120
End Postision file is  357
Event type ('\x1f') is an update v2
We got an update!!
Ready to revert the statement ? [y/n]
y
Sending to mysql...
Done... I hope it worked ;)

mysql> select * from fred;
+----+------------+
| id | name       |
+----+------------+
|  1 | Fred       |
|  2 | Jen        |
|  3 | Wilhelmine |
|  4 | Héloïse    |
|  5 | Suhi       |
+----+------------+
5 rows in set (0.00 sec)
```
