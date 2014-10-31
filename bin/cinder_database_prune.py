import MySQLdb
import sys
import os

db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_host = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

db = MySQLdb.connect(db_host, db_user, db_pass, db_name)

days = 14
limit = 1000
finished = 0
cleaned = 0

print """Starting clean of deleted volumes older then %s days , 
        in groups of %s""" % (days, limit)

while (finished < 1):
        db.autocommit(False)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        s = """SELECT * FROM volumes WHERE status='deleted' AND deleted !=0 
        AND deleted_at < DATE_SUB(NOW(), INTERVAL %s day)
        order by deleted_at LIMIT %s""" % (days, limit)
        cursor.execute(s)
        results = cursor.fetchall()
        ids = []
        for row in results:
                ids.append(row["id"])

        if len(ids) < 1:
                print "finished!"
                finished = 1
        break

        try:
                print "Cleaning volumes %s" % (', ').join(ids)
                sql_str = ','.join(['%s'] * len(ids))
                # clean metadata
                cursor.execute("DELETE FROM volume_metadata WHERE volume_id IN (%s)" % (sql_str), ids)
                cursor.execute("DELETE FROM volume_glance_metadata  WHERE volume_id IN (%s)" % (sql_str), ids)
                cursor.execute("DELETE FROM volume_admin_metadata WHERE volume_id IN (%s)" % (sql_str), ids)


              # snapshots
                cursor.execute("SELECT id FROM snapshots WHERE volume_id  IN (%s)" % (sql_str), ids)
                snapids = []
                results = cursor.fetchall()
                for snap in results:
                        snapids.append(snap["id"])

                if len(snapids):
                        print "Snapshots to delete!"
                        snap_str = ','.join(['%s'] * len(snapids))
                        cursor.execute("""DELETE FROM volume_glance_metadata WHERE 
                                        snapshot_id IN (%s)""" % (snap_str), snapids)
                        cursor.execute("""DELETE FROM snapshots WHERE id IN (%s) AND
                                        status='deleted' AND deleted='1'""" % (snap_str), snapids)

                cursor.execute("DELETE FROM volumes WHERE id IN (%s)" % (sql_str), ids)
                db.commit()
        except db.Error, e:
                print "Rollback %s %s" % (e[0], e[1])
                db.rollback()
                sys.exit(1)

        cleaned += limit
        print "Finished cleaning %s" % cleaned

print "Cleaning up reservations"
try:
        db.autocommit(False)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("DELETE FROM reservations WHERE expire < DATE_SUB(NOW(), INTERVAL %s day)" % days)
        db.commit()
except db.Error, e:
        print "Rollback %s %s" % (e[0], e[1])
        db.rollback()
        sys.exit(1)


db.close()
