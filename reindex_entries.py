#!blog/bin/python


#
# Imports
#

import sqlite3
import app
import os


#
# SQLite objects and queries
#

conn = sqlite3.connect("blog.db", timeout = 10)
curs = conn.cursor()

delete_query = "DELETE FROM {}"
query = "SELECT * FROM entry"


#
# Methods
#

def drop_ancillary_tables():
	# these are the ancillary tables
	f = "ftsentry"
	fc = "ftsentry_content"
	fd = "ftsentry_docsize"
	fs = "ftsentry_segdir"
	fsg = "ftsentry_segments"
	fst = "ftsentry_stat"

	# these are consolidated
	tables = [f, fc, fd, fs, fsg, fst]

	# iterate and delete from each
	for table in tables:
		curs.execute(delete_query.format(table))
		conn.commit()

def drop_entry_table():
	curs.execute(delete_query.format("entry"))
	conn.commit()


def create_entry(title, slug, content, published, timestamp):
	# create entry from constructor
	entry = app.Entry(title = title, 
		slug = slug, 
		content = content, 
		published = published, 
		timestamp = timestamp)

	return entry


#
# Main
#

def main():
	# for tracking all entries so far
	all_entries = []

	# drop all ancillary tables
	drop_ancillary_tables()

	# for each entry, let's get it and extract as Entry object, persist in memory for now
	try:
		for row in curs.execute(query):
			title = row[1]
			slug = row[2]
			content = row[3]
			published = row[4]
			timestamp = row[5]

			# create entry, append to list
			entry = create_entry(title, slug, content, published, timestamp)
			all_entries.append(entry)

		# now drop entry table
		drop_entry_table()

		# for each entry now in memory, save
		for entry in all_entries:
			entry.save()

	except Exception as e:
		print("Exception: {}".format(str(e)))

	finally:
		curs.close()
		conn.close()


#
# Execution
#

if __name__ == "__main__":
	main()
