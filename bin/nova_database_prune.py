#!/usr/bin/env python
import MySQLdb
import sys
import os

db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

db = MySQLdb.connect(db_host, db_user, db_pass, db_name)

# days to keep
days = 14
# batch size for deletes
limit = 1000


print "Cleaning instances older than %s days , in groups of %s" % (days, limit)

finished = 0
cleaned = 0

while (finished < 1):
        db.autocommit(False)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        s = """SELECT * FROM instances WHERE deleted !=0 and deleted_at <
        DATE_SUB(NOW(), INTERVAL %s day) order by deleted_at
        LIMIT %s""" % (days, limit)
        cursor.execute(s)
        results = cursor.fetchall()
        ids = []
        for row in results:
                ids.append(row["uuid"])

        if len(ids) < 1:
                print "finished!"
                finished = 1
                break
        try:
                print "Removing %s " % (', ').join(ids)
                sql_str = ','.join(['%s'] * len(ids))
                cursor.execute("""SELECT id from instance_actions where
                                instance_uuid  in (%s)""" % (sql_str), ids)
                iae = []
                results = cursor.fetchall()
                for event in results:
                        iae.append(event["id"])

                if len(iae):
                        iae_str = ','.join(['%s'] * len(iae))
                        cursor.execute("""DELETE from instance_actions_events 
                                        WHERE action_id in (%s)""" % (iae_str), iae)

                cursor.execute("DELETE from instance_actions where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from instance_info_caches where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from instance_system_metadata where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from instance_faults where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from instance_metadata where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from block_device_mapping where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from migrations where instance_uuid in (%s)" % (sql_str), ids)
                cursor.execute("DELETE from instances where uuid in (%s)" % (sql_str), ids)
                db.commit()
        except db.Error, e:
                print "Rollback %s %s" % (e[0], e[1])
                db.rollback()
                sys.exit(1)

        cleaned += limit
        print "Finished cleaning %s " % cleaned


print "Cleaning up reservations / stats"
try:
        db.autocommit(False)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""DELETE FROM reservations WHERE expire
                        < DATE_SUB(NOW(), INTERVAL %s day)""")
        cursor.execute("""DELETE FROM compute_node_stats WHERE deleted_at
                        < DATE_SUB(NOW(), INTERVAL %s day)""")
        db.commit()
except db.Error, e:
        print "Rollback %s %s" % (e[0], e[1])
        db.rollback()
        sys.exit(1)

db.close()
