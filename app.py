#!blog/bin/python


#
# Imports
#

import datetime
import functools
import os
import re
import urllib

# todo: research abort, flash, request, Response
# todo: research how url_for() method works
from flask import (Flask, abort, flash, Markup, redirect, render_template, 
	request, Response, session, url_for)

# todo: research
from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension

# todo: research
from micawber import bootstrap_basic, parse_html
from micawber.cache import Cache as OEmbedCache

# todo: research
from peewee import *

# todo: research
from playhouse.flask_utils import FlaskDB, get_object_or_404, object_list
from playhouse.sqlite_ext import *


#
# Application constants and configurations
#

ADMIN_PASSWORD = os.environ.get("FLASK_BLOG_ADMIN_PASSWORD")
APP_DIR = os.path.dirname(os.path.realpath(__file__))
DEBUG = False

# the playhouse.flask_utils.FlaskDB object accepts database URL configuration.
DATABASE_PATH = os.path.join(APP_DIR, "blog.db") 
DATABASE = "sqliteext:///{}?check_same_thread=False".format(DATABASE_PATH)

# todo: research
# todo: externalize this key to an more secure location (or use one-way hashing)
# used by Flask to encrypt session cookie
SECRET_KEY = "shhh, secret!"  

# todo: research
# used by micawber, which will attempt to generate rich media
# embedded objects with maxwidth = 800.
SITE_WIDTH = 800

# todo: research
# creating a Flask WSGI app, configure it with values from module
app = Flask(__name__)
app.config.from_object(__name__)

# todo: research
# FlaskDB wraps application object, allowing pre/post-request hooks
# for managing database connections
flask_db = FlaskDB(app)

# todo: research
# actual peewee database (as opposed to flask_db, which is only wrapper)
database = flask_db.database

# todo: research
# configure micawber with the default OEmbed providers (YouTube, Flickr, etc).
# to use a simple in-memory cache so that multiple requests for the same
# video don't require multiple network requests
oembed_providers = bootstrap_basic(OEmbedCache())


#
# Entities
#

class Entry(flask_db.Model):
	title = CharField() # maybe this object comes from peewee...
	slug = CharField(unique = True) # note: constraints can apply
	content = TextField()
	published = BooleanField(index = True) # note: how to index
	timestamp = DateTimeField(default = datetime.datetime.now, index = True) # note: how to provide defaults

	@property
	def html_content(self):
		# todo: research what all these things do
		hilite = CodeHiliteExtension(linenums = False, css_class = "highlight")
		extras = ExtraExtension()
		markdown_content = markdown(self.content, extensions = [hilite, extras])
		oembed_content = parse_html(
			markdown_content, 
			oembed_providers, 
			urlize_all = True, 
			maxwidth = app.config["SITE_WIDTH"])
		return Markup(oembed_content)

	# a hackneyed convience method for the first page
	# 	displaying only the first few characters of a thing
	def html_content_preview(self, limit):
		hilite = CodeHiliteExtension(linenums = False, css_class = "highlight")
		extras = ExtraExtension()

		# adding ellipsis if necessary, otherwise entire content is the preview
		if (len(self.content) <= limit):
			markdown_content = markdown(self.content, extensions = [hilite, extras])
		else:
			markdown_content = markdown(self.content[:limit - 3] + "&hellip;", extensions = [hilite, extras])

		oembed_content = parse_html(
			markdown_content, 
			oembed_providers, 
			urlize_all = True, 
			maxwidth = app.config["SITE_WIDTH"])
		return Markup(oembed_content)

	def save(self, *args, **kwargs):
		# if no slug, then create one out of blog post title
		if not self.slug:
			self.slug = re.sub("[^\w]+", "-", self.title.lower())

		# todo: research what this is doing under the hood
		# what is happening with the fields?
		# what is returned?
		ret = super(Entry, self).save(*args, **kwargs)

		# todo: research
		self.update_search_index()

		# todo: why returning?
		return ret

	# todo: research why need to pass self here
	def update_search_index(self):
		try:
			fts_entry = FTSEntry.get(FTSEntry.entry_id == self.id)
		except FTSEntry.DoesNotExist:
			fts_entry = FTSEntry(entry_id = self.id)
			force_insert = True
		else:
			force_insert = False
		# one long string is title plus the content
		fts_entry.content = "\n".join((self.title, self.content))

		# todo: research if force_insert is something like "upsert" or not
		fts_entry.save(force_insert = force_insert)

	def _delete(self, *args, **kwargs):
		# todo: research why delete_instance() isn't work the way i'd expect it to
		query = Entry.delete()\
					 .where(Entry.id == self.id)
		query.execute()

		# go on and delete the relevant FTS tables
		self.update_search_index_delete()

	def update_search_index_delete(self):
		# todo: consider wrapping this in a try?
		query = FTSEntry.delete()\
						.where(FTSEntry.entry_id == self.id)
		query.execute()

	@classmethod
	def public(cls):
		return Entry.select()\
					.where(Entry.published == True)

	@classmethod
	def search(cls, query):
		words = [word.strip() for word in query.split() if word.strip()]
		if not words:
			# return empty entity???
			return Entry.select()\
						.where(Entry.id == 0)
		else:
			search = " ".join(words)

		# todo: research how this kind of in-code query works
		# http://charlesleifer.com/blog/using-sqlite-full-text-search-with-python/
		return (FTSEntry
			.select(
				FTSEntry, 
				Entry, 
				FTSEntry.rank().alias("score"))
			.join(Entry, on = (FTSEntry.entry_id == Entry.id).alias("entry"))
			.where(
				(Entry.published == True) & 
				(FTSEntry.match(search)))
			.order_by(SQL("score").desc()))

	@classmethod
	def drafts(cls):
		return Entry.select()\
					.where(Entry.published == False)

class FTSEntry(FTSModel):
	entry_id = IntegerField()
	content = TextField()

	def _get_pk_value(self):
		"""
		This is a hack, I think. Look at the documentation here: https://github.com/coleifer/peewee/blob/master/peewee.py - 
		particulary at the save() method on line 5059. For whatever reason, _get_pk_value() method of my particular FTSEntry class
		is returning None. What it _should_ return is the docid stored internally by SQLite.
		Should try and figure out why this is the case.
		"""
		return self.docid

	# todo: research what use this is
	class Meta:
		database = database


#
# todo: finish this entity
#

class Comment(flask_db.Model):

	author = CharField()
	content = TextField()
	timestamp = DateTimeField(default = datetime.datetime.now, index = True)

	def save(self, *args, **kwargs):
		return super(Comment, self).save(*args, **kwargs)


#
# Handlers
#

def login_required(fn):
	@functools.wraps(fn)
	def inner(*args, **kwargs):
		if session.get("logged_in"):
			return fn(*args, **kwargs)
		return redirect(url_for("login", next = request.path))
	return inner

@app.route("/login/", methods = ["GET", "POST"])
def login():
	# takes query parameters and takes user to the page they want after logging in
	next_url = request.args.get("next") or request.form.get("next")

	# if POST (ie. logging in), then send them to appropriate location (generally, the index page)
	if request.method == "POST" and request.form.get("password"):
		password = request.form.get("password")
		if password == app.config["ADMIN_PASSWORD"]:
			session["logged_in"] = True

			# todo: research this as well as statement below
			# use cookie to store session
			session.permanent = True  
			flash("You are now logged in.", "success")
			return redirect(next_url or url_for("index"))
		else:
			flash("Incorrect password.", "danger")
	# if GET (ie. want to go to login), then send to login page
	return render_template("login.html", next_url = next_url)

@app.route("/logout/", methods = ["GET", "POST"])
def logout():
	if request.method == "POST":
		# cleaning all session of its attributes
		session.clear()
		return redirect(url_for("login"))
	return render_template("logout.html")

@app.route("/")
def index():
	search_query = request.args.get("q")
	# interesting way to render the home page!
	if search_query:
		query = Entry.search(search_query)
	else:
		query = Entry.public()\
					 .order_by(Entry.timestamp.desc())

	# because, either way, the stuff will get rendered!

	# todo: research why i had to add check_bounds = False
	# todo: research more on this method (pagination, especially) here: http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#object_list
	return object_list("index.html", query, paginate_by = 5, check_bounds = False, search = search_query)

@app.route("/about")
def about():
	return render_template("about.html")

@app.route("/drafts/")
@login_required
def drafts():
	query = Entry.drafts()\
				 .order_by(Entry.timestamp.desc())
	return object_list("index.html", query, paginate_by = 5, check_bounds  = False, title = "Drafts")


### THIS IS A UTILITY METHOD
def _create_or_edit(entry, template):
	# if submitting data
	if request.method == "POST":
		# extract data (kind of like "or-equals" in Ruby)
		entry.title = request.form.get("title") or ""
		entry.content = request.form.get("content") or ""
		entry.published = request.form.get("published") or False

		if not (entry.title and entry.content):
			flash("Title and Content are required.", "danger")
		else:
			# wrap the call to save in a transaction so we can roll it back
			# cleanly in the event of an integrity error
			try:
				with database.atomic():
					# todo: make sure the appropriate entry in the Metatable is updated
					entry.save()
			except IntegrityError:
				flash("Error: this title is already in use.", "danger")
			else:
				flash("Entry saved successfully.", "success")
				# appropriately redirect, dependent on what type of POST we made
				if entry.published:
					return redirect(url_for("detail", slug = entry.slug))
				else:
					return redirect(url_for("edit", slug = entry.slug))

	# if simply navigating to this page, then return appropriate page
	return render_template(template, entry = entry)


@app.route("/create/", methods = ["GET", "POST"])
@login_required
def create():
	# an empty Entry (not yet persisted)
	return _create_or_edit(Entry(title = "", content = ""), "create.html")

@app.route("/<slug>/edit/", methods = ["GET", "POST"])
@login_required
def edit(slug):
	# first get the correct entry, then redirect
	entry = get_object_or_404(Entry, Entry.slug == slug)
	return _create_or_edit(entry, "edit.html")

@app.route("/<slug>/")
def detail(slug):
	# makes sense to have these two things for public and private viewing
	# todo: think about whether there would be any use of "private" entries other than for drafts
	if session.get("logged_in"):
		query = Entry.select()
	else:
		query = Entry.public()
	# todo: research how this method works
	entry = get_object_or_404(query, Entry.slug == slug)
	return render_template("detail.html", entry = entry)

@app.route("/<slug>/delete")
@login_required
def delete(slug):
	# get particular entry and delete
	entry = Entry.get(Entry.slug == slug)
	entry._delete()

	# redirect towards index page
	return redirect(url_for("index"))


#
# Application intiailization code
#

@app.template_filter("clean_querystring")
def clean_querystring(request_args, *keys_to_remove, **new_values):
	# assume some data will be passed along in request argument object
	# todo: research more about the request object
	querystring = dict((key, value) for key, value in request_args.items())

	# simple removes these entries from the dictionary
	for key in keys_to_remove:
		querystring.pop(key, None)

	# todo: research what update() method does for a dict object
	querystring.update(new_values)
	return urllib.urlencode(querystring) # HTTP-compatible rendering of dictionary object?

@app.errorhandler(404)
def not_found(exc):
	# seems like it returns fully rendered HTML plus a response code
	return Response("<h3>Not found</h3>"), 404

def main():
	# for specifying files to watch: http://stackoverflow.com/questions/9508667/reload-flask-app-when-template-file-changes
	# todo: remove for production
	extra_dirs = [os.path.join(APP_DIR, "templates/"),]
	extra_files = extra_dirs[:]
	for extra_dir in extra_dirs:
		for dirname, dirs, files in os.walk(extra_dir):
			for filename in files:
				filename = os.path.join(dirname, filename)
				if os.path.isfile(filename):
					extra_files.append(filename)

	# this creates tables if non existent already
	# todo: research what the safe argument is good for
	database.create_tables([Entry, FTSEntry], safe = True)
	app.run(debug = DEBUG, extra_files = extra_files)


#
# Running the thing
#

if __name__ == "__main__":
	main()


